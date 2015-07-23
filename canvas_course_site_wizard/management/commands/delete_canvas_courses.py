from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from datetime import datetime
from canvas_course_site_wizard.controller import get_canvas_course_url
from canvas_course_site_wizard.models import SISCourseData, CanvasCourseGenerationJob
from canvas_course_site_wizard.models_api import get_course_data
from canvas_sdk.exceptions import CanvasAPIError
from canvas_sdk.methods import sections, enrollments, courses
from canvas_sdk.utils import get_all_list_data
from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.models import CourseInstance, CourseSite
import logging

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'This command will process courses by deleting the enrollments, '
        'sections and course from the Canvas database. '
        'It accepts a list of Canvas course IDs to delete.\n\n'
        'For example:\n\n'
        '> python manage.py delete_canvas_courses 1000 1001 1002'
    )
    option_list = BaseCommand.option_list + (
        make_option('-b', '--bulk-job-id',
                    action='store',
                    dest='bulk_job_id',
                    default=None,
                    help='If specified, this option will delete all the Canvas courses '
                         'that were created by the given bulk job'),
        make_option('-c', '--course-instance-ids',
                    action='store_true',
                    dest='course_instance_ids',
                    default=False,
                    help='If specified, this option will treat the course IDs provided '
                         'as (CourseManager) Course Instance IDs instead of Canvas course IDs. '),
        make_option('-s', '--skip-sis-updates',
                    action='store_true',
                    dest='skip_sis_updates',
                    default=False,
                    help='Only update Canvas; will not touch the '
                         'CourseManager data'),
    )

    def handle(self, *args, **options):
        """
        This process is to clean up Canvas courses and, if specified, their
        associated CourseManager data
        """
        ids = args
        bulk_job_id = options.get('bulk_job_id')
        lookup_canvas_id = options.get('course_instance_ids')
        skip_sis_updates = options.get('skip_sis_updates')

        if lookup_canvas_id and bulk_job_id:
            raise CommandError("You cannot combine the course-instance-ids and bulk-job-id options.")

        if not len(args) and not bulk_job_id:
            logger.info('No course to process')
            return

        start_time = datetime.now()

        if bulk_job_id:
            query_set = CanvasCourseGenerationJob.objects.filter(
                bulk_job_id=bulk_job_id,
                canvas_course_id__isnull=False
            )
            ids.extend([job.canvas_course_id for job in query_set])

        for course_id in ids:
            # Checking to see if we are looking at non-canvas course ids
            # Verify that the course id exist in the course manager db
            # if so, modify the course_id parameter to search by the
            # sis_course_id, instead of the canvas course id
            if lookup_canvas_id:
                canvas_course_lookup_id = get_canvas_course_lookup_id(course_id)
            else:
                canvas_course_lookup_id = course_id

            if canvas_course_lookup_id:
                process_course(canvas_course_lookup_id, skip_sis_updates)

        logger.info('command took %s seconds to run'
                    % str(datetime.now() - start_time)[:-7])


def get_canvas_course_lookup_id(sis_course_id):
    """
    return a Canvas id in the format sis_course_id:____ for looking up a course
     in Canvas based on SIS course ID provided
    """
    try:
        if CourseInstance.objects.filter(pk=sis_course_id).count() > 0:
            return 'sis_course_id:%s' % sis_course_id
        else:
            logger.info('Course instance %s does not exist in Course Manager '
                        'database' % sis_course_id)
    except Exception as e:
        logger.error('Error trying to read the course manager db for '
                     'course instance %s: %s' % (sis_course_id, e))
    return None  # error finding course or course not found in Course Manager db


def process_course(canvas_course_lookup_id, skip_sis_updates=False):
    """
    manages the deletion of an individual course. canvas_course_lookup_id is
     used to locate the course in Canvas. This method determines the canonical
     Canvas ID, verifies the course exists in Canvas, then calls helpers to
     remove Canvas course sections (including enrollments),
     delete the course from Canvas, and update the CourseManager records.
    """
    if canvas_course_lookup_id is None:
        logger.info('No course to process')
        return

    # get the canonical Canvas course ID and SIS course ID (verify the course
    # exists, and if canvas_course_lookup_id is prefixed by sis_course_id,
    # from this point forward use the actual Canvas course ID)
    canvas_course_json = validate_course(canvas_course_lookup_id)

    if not canvas_course_json:
        logger.info('Course %s not found in Canvas' % canvas_course_lookup_id)
        return

    canvas_course_id = canvas_course_json.get('id')
    sis_course_id = canvas_course_json.get('sis_course_id')
    if sis_course_id == '':
        sis_course_id = None

    logger.debug(
        'Processing canvas course %s with sis_course_id %s'
        % (canvas_course_id, sis_course_id if sis_course_id else '(none)')
    )

    if not skip_sis_updates:
        unmark_course_as_official(canvas_course_id)
        if sis_course_id:
            unsync_from_canvas_and_reset_canvas_id(sis_course_id)
        else:
            logger.warn(
                'Canvas course %s does not have an SIS ID in Canvas; if an '
                'associated course exists in CourseManager it will not '
                'be un-synced (the CourseInstance will not be updated).'
                % canvas_course_id
            )

    canvas_sections = get_list_sections(canvas_course_id)
    process_sections(canvas_sections, canvas_course_id)
    delete_course(canvas_course_id)


def validate_course(canvas_course_lookup_id):
    """ Verify that the course exists in Canvas db and return canvas course """
    try:
        canvas_course_json = courses.get_single_course_courses(
            SDK_CONTEXT, canvas_course_lookup_id, include='all_courses').json()
    except CanvasAPIError as api_error:
        logger.error('Error looking up course %s in Canvas: %s'
                     % (canvas_course_lookup_id, api_error))
        return None
    return canvas_course_json


def get_list_sections(canvas_course_id):
    """ Get a list of sections for the course """
    canvas_sections = []
    try:
        canvas_sections = get_all_list_data(SDK_CONTEXT, sections.list_course_sections, canvas_course_id)
    except CanvasAPIError as api_error:
        logger.error('Error trying to get list of sections for course %s: %s' % (canvas_course_id, api_error))

    return canvas_sections


def process_sections(canvas_sections, canvas_course_id):
    """ Organizes steps required to delete all sections in canvas_sections list from the course """
    if not len(canvas_sections):
        logger.debug('No sections for Canvas course %s' % canvas_course_id)

    for section in canvas_sections:
        section_id = section.get('id')
        if section_id:
            delete_enrollments_for_section(section_id, canvas_course_id)
            delete_section(section_id, canvas_course_id)


def delete_enrollments_for_section(section_id, canvas_course_id):
    """ Deletes all enrollments from the section """
    canvas_enrollments = []
    # get a list of enrollments
    try:
        canvas_enrollments = get_all_list_data(SDK_CONTEXT, enrollments.list_enrollments_sections, section_id)
    except CanvasAPIError as api_error:
        logger.error('Error trying to get list of enrollments for '
                     'Canvas course %s for section %s: %s'
                     % (canvas_course_id, section_id, api_error))
        return

    # delete each enrollment
    for enrollment in canvas_enrollments:
        canvas_course_id_for_section = enrollment.get('course_id', '(none)')
        enrollment_id = enrollment.get('id', '(none)')
        try:
            response = enrollments.conclude_enrollment(
                SDK_CONTEXT, canvas_course_id_for_section, enrollment_id, task='delete')
        except CanvasAPIError as api_error:
            logger.error('Error trying to delete enrollment %s (course_id %s) '
                         'from Canvas course %s: %s'
                         % (enrollment_id, canvas_course_id_for_section,
                            canvas_course_id, api_error))


def delete_course(canvas_course_id):
    """ Deletes a course from Canvas (assumes sections and enrollments are already deleted) """
    try:
        # Remove the SIS ID from the course first; otherwise trying to create a course with that same SIS section ID
        # will fail in the future (because it's a soft delete in the Canvas database)
        response = courses.update_course(SDK_CONTEXT, canvas_course_id, course_sis_course_id='')
    except CanvasAPIError as api_error:
        logger.error('Error trying to remove the course SIS ID from '
                     'Canvas course %s: %s' % (canvas_course_id, api_error))

    try:
        response = courses.conclude_course(SDK_CONTEXT, canvas_course_id, event='delete')
    except CanvasAPIError as api_error:
        logger.error('Error trying to delete Canvas course %s: %s' % (canvas_course_id, api_error))


def delete_section(section_id, canvas_course_id):
    """ Deletes a section from a course (assumes enrollments are already deleted) """
    try:
        # Remove the SIS ID from the section first; otherwise trying to create a section with that same SIS section ID
        # will fail in the future (because it's a soft delete in the Canvas database)
        response = sections.edit_section(SDK_CONTEXT, section_id, course_section_sis_section_id='')
    except CanvasAPIError as api_error:
        logger.error('Error trying to remove the section SIS ID from section %s '
                     'for Canvas course %s: %s'
                     % (section_id, canvas_course_id, api_error))

    try:
        response = sections.delete_section(SDK_CONTEXT, section_id)
    except CanvasAPIError as api_error:
        logger.error('Error trying to delete section %s for Canvas course %s: '
                     '%s' % (section_id, canvas_course_id, api_error))


def unsync_from_canvas_and_reset_canvas_id(sis_course_id):
    """
    Turns off Canvas sync (via the feed) and removes Canvas course ID
    associated with a given Course Instance
    """
    sis_course_data = None

    try:
        sis_course_data = get_course_data(sis_course_id)
        sis_course_data.set_sync_to_canvas(
            SISCourseData.TURN_OFF_SYNC_TO_CANVAS
        )
        logger.debug('Turned off SIS enrollment data sync for '
                     'course instance %s' % sis_course_id)
    except Exception as e:
        logger.error('Error setting SIS enrollment data sync flag for '
                     'course instance %s: %s' % (sis_course_id, e))

    if sis_course_data:
        try:
            sis_course_data.canvas_course_id = None
            sis_course_data.save()
            logger.debug('Removed canvas course ID for course instance %s'
                         % sis_course_id)
        except Exception as e:
            logger.error('Error removing canvas course ID for '
                         'course instance %s: %s' % (sis_course_id, e))


def unmark_course_as_official(canvas_course_id):
    """ Removes Canvas site mapping (CourseSite and SiteMap) for a course """
    try:
        canvas_course_url = get_canvas_course_url(
            canvas_course_id=canvas_course_id
        )
        site = CourseSite.objects.get(
            external_id=canvas_course_url, site_type_id='external'
        )
        # deleting the CourseSite object also deletes the associated SiteMap
        site.delete()
        logger.debug('Removed official site mapping for Canvas course %s'
                     % canvas_course_id)
    except Exception as e:
        logger.error('Error removing official site mapping for '
                     'Canvas course %s: %s' % (canvas_course_id, e))
