from datetime import datetime
import fcntl
import logging

from django.core.management.base import NoArgsCommand
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from canvas_course_site_wizard.controller import (get_canvas_user_profile,
                                                  send_email_helper,
                                                  create_canvas_course,
                                                  get_course_data,
                                                  start_course_template_copy)
from canvas_course_site_wizard.models import (BulkCanvasCourseCreationJob as BulkJob,
                                              CanvasCourseGenerationJob)
from canvas_course_site_wizard.exceptions import (NoTemplateExistsForSchool,
                                                  CanvasCourseAlreadyExistsError,
                                                  CourseGenerationJobCreationError,
                                                  CanvasCourseCreateError,
                                                  CanvasSectionCreateError)
from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.models import Term, School

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

logger = logging.getLogger(__name__)
tech_logger = logging.getLogger('tech_mail')


class Command(NoArgsCommand):
    """
    Process the Bulk course creation jobs. PENDING bulk jobs without non-terminal subjobs will be 'finalized':
      the bulk job creator will be notified via email and the bulk job status will indicate it is no longer pending.
    To invoke this Command type "python manage.py finalize_bulk_create_jobs".
    """
    help = "Notifies the user and/or support team for any bulk course create jobs which are finished"

    def handle_noargs(self, **options):

        # open and lock the file used for determining if another process is running
        _pid_file = getattr(settings, 'FINALIZE_BULK_CREATE_JOBS_PID_FILE', 'finalize_bulk_create_jobs.pid')
        _pid_file_handle = open(_pid_file, 'w')
        try:
            fcntl.lockf(_pid_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            # another instance is running
            logger.error("another instance of the command is already running")
            return

        start_time = datetime.now()

        ###
        # process CanvasContentMigrationJobs with  workflow_state = 'setup'
        ###
        _init_courses_with_status_setup()

        ###
        # Process to finalize the bulk job
        ###

        jobs = BulkJob.objects.get_jobs_by_status(BulkJob.STATUS_PENDING)

        jobs_count = len(jobs)
        if not jobs_count:
            logger.info('No pending bulk create jobs found.')
        else:
            logger.info('Found %d pending bulk create jobs.', jobs_count)

        for job in jobs:
            logger.debug('Checking if all subjobs are finished for pending bulk create job %s ', job.id)
            if not job.ready_to_finalize():
                logger.debug('Job %s is not ready to be finalized, leaving pending.', job.id)
                continue

            logger.info('Finalizing job %s...', job.id)

            if not job.update_status(BulkJob.STATUS_FINALIZING):
                logger.exception("Job %s: problem saving finalization status", job.id)
                continue

            logger.debug('Job %s status updated to %s, notifying job creator %s...',
                         job.id, job.status, job.created_by_user_id)

            job_notification_status = BulkJob.STATUS_NOTIFICATION_SUCCESSFUL  # assumes notification success

            if not _send_notification(job):
                job_notification_status = BulkJob.STATUS_NOTIFICATION_FAILED

            if not job.update_status(job_notification_status):
                logger.exception("Job %s: problem saving notification status", job.id)
                continue

            logger.info('Job %s status updated to %s', job.id, job.status)

        _log_bulk_job_statistics()

        logger.info('command took %s seconds to run', str(datetime.now() - start_time)[:-7])

        # unlock and close the file used for determining if another process is running
        try:
            fcntl.lockf(_pid_file_handle, fcntl.LOCK_UN)
            _pid_file_handle.close()
        except IOError:
            logger.error("could not release lock on pid file or close pid file properly")

def _init_courses_with_status_setup():
    """
    get all records in the canvas course generation job table that have the status 'setup'.
    These are courses that have not been created, they only have a CanvasCourseGenerationJob with a 'setup' status.
    This method will create the course and update the status to QUEUED
    """

    create_jobs = CanvasCourseGenerationJob.objects.filter_setup_for_bulkjobs()
    # Get the bulk job parent for each course job and map by id for later use
    bulk_jobs = {b.id: b for b in BulkJob.objects.filter(id__in=[j.bulk_job_id for j in create_jobs])}

    # for each or the records above, create the course and update the status
    for create_job in create_jobs:
        # for each job we need to get the bulk_job_id, user, and course id, these are
        # needed by the calls to create the course below. If any of these break, mark the course as failed
        # and continue to the next course.
        bulk_job = bulk_jobs.get(create_job.bulk_job_id)
        if not bulk_job:
            create_job.update_workflow_state(CanvasCourseGenerationJob.STATUS_SETUP_FAILED)
            continue
        bulk_job_id = bulk_job.id

        sis_user_id = create_job.created_by_user_id
        if not sis_user_id:
            create_job.update_workflow_state(CanvasCourseGenerationJob.STATUS_SETUP_FAILED)
            continue

        sis_course_id = create_job.sis_course_id
        if not sis_course_id:
            create_job.update_workflow_state(CanvasCourseGenerationJob.STATUS_SETUP_FAILED)
            continue

        # try to create the canvas course - create_canvas_course has been modified so it will not
        # try to create a new CanvasCourseGenerationJob record if a bulk_job is present
        try:
            logger.info(
                'calling create_canvas_course(%s, %s, bulk_job_id=%s)',
                sis_course_id, sis_user_id,
                bulk_job_id
            )
            course = create_canvas_course(sis_course_id, sis_user_id, bulk_job_id=bulk_job_id)
        except (CanvasCourseAlreadyExistsError, CourseGenerationJobCreationError, CanvasCourseCreateError,
                CanvasSectionCreateError):
            message = 'content migration error for course with id %s' % sis_course_id
            logger.exception(message)
            create_job.update_workflow_state(CanvasCourseGenerationJob.STATUS_SETUP_FAILED)
            continue

        # get the course data - this is needed for the start_course_template_copy method
        try:
            sis_course_data = get_course_data(sis_course_id)
        except ObjectDoesNotExist as ex:
            message = 'Course id %s does not exist, skipping....' % sis_course_id
            logger.exception(message)
            create_job.update_workflow_state(CanvasCourseGenerationJob.STATUS_SETUP_FAILED)
            continue

        # Initiate the async job to copy the course template, if a template was selected for the bulk job
        if bulk_job.template_canvas_course_id:
            try:
                start_course_template_copy(
                    sis_course_data,
                    course['id'],
                    sis_user_id,
                    course_job_id=create_job.pk,
                    bulk_job_id=bulk_job_id,
                    template_id=bulk_job.template_canvas_course_id
                )
            except:
                logger.exception('template migration failed for course instance id %s' % sis_course_id)
                create_job.update_workflow_state(CanvasCourseGenerationJob.STATUS_SETUP_FAILED)
        else:
            logger.info('no template selected for  %s' % sis_course_id)
            # When there's no template, it doesn't need any migration and the job is ready to be finalized
            create_job.update_workflow_state(CanvasCourseGenerationJob.STATUS_PENDING_FINALIZE)


def _send_notification(job):
    """
    helper function to encapsulate the process of sending a report via email to the user who created the bulk job
    :param job: a BulkJob
    :return: True if notification was successfully sent (passed to the Django framework, anyway);
             False if no notification was sent
    """
    notification_to_address_list = []
    canvas_user_profile = None

    logger.debug("Looking up notification email recipient address list...")

    try:
        canvas_user_profile = get_canvas_user_profile(job.created_by_user_id)
        notification_to_address_list = [canvas_user_profile['primary_email']]
    except Exception as e:
        # todo: do we need all these multilayered logs?
        error_text = (
            "Job %s: problem getting canvas user profile for user %s" % (job.id, job.created_by_user_id)
        )
        logger.exception(error_text)
        _log_notification_failure(job)
        return False

    logger.debug("Building notification email...")

    completed_subjobs = job.get_completed_subjobs_count()
    failed_subjobs = job.get_failed_subjobs_count()

    try:
        term = Term.objects.get(term_id=int(job.sis_term_id))
        term_display_name = term.display_name
        school = School.objects.get(school_id=job.school_id)
        school_display_name = school.title_short
    except Exception as e:
        error_text = (
            "Canvas course create bulk job %s: "
            "problem getting user-friendly term or school name"
        )
        logger.exception(error_text)
        term_display_name = job.sis_term_id
        school_display_name = job.school_id

    subject = _format_notification_email_subject(
        school_display_name,
        term_display_name
    )
    body = _format_notification_email_body(
        school_display_name,
        term_display_name,
        completed_subjobs,
        failed_subjobs
    )

    logger.debug("Sending notification email to %s...", notification_to_address_list)

    try:
        send_email_helper(subject, body, notification_to_address_list)
    except Exception as e:
        # todo: do we need all these multilayered logs?
        logger.exception("Job %s: problem sending notification", job.id)
        _log_notification_failure(job)
        return False

    logger.debug("Notification email sent!")
    return True


def _format_notification_email_subject(school_name, term_name):
    """
    helper method to create an email subject for a bulk canvas course create job
    notification email
    :param school_name: string, user-friendly school name, e.g. 'colgsas'
    :param term_name: string, user-friendly name for the job's SIS term
    :return: string, email subject line
    """
    subject = settings.BULK_COURSE_CREATION['notification_email_subject']
    return subject.format(school=school_name, term=term_name)


def _format_notification_email_body(school_name, term_name, completed_count,
                                    failed_count):
    """
    helper method to create an email body (essentially a report) for a bulk
    canvas course create job notification email
    :param school_name: string, user-friendly name for school, e.g. 'colgsas'
    :param term_name: string, user-friendly name for bulk job's SIS term
    :param completed_count: integer, number of completed courses
      (to report as successfully processed)
    :param failed_count: integer, number of failed courses
      (to report as unsuccessfully processed)
    :return: string, email body text
    """
    body = settings.BULK_COURSE_CREATION['notification_email_body']
    body = body.format(
        school=school_name,
        term=term_name,
        success_count=completed_count
    )
    failed = settings.BULK_COURSE_CREATION['notification_email_body_failed_count']
    if failed_count:
        body += failed.format(failed_count)
    return body


def _log_notification_failure(job):
    """
    a helper method called if user notification failed; will log the failure and notify tech support
    :param job: a BulkJob
    """
    try:
        error_text = (
            "There was a problem in sending bulk job failure notification email to initiator %s "
            "and support staff for bulk job %s" % (job.created_by_user_id, job.id)
        )
    except Exception as e:
        error_text = "There was a problem in sending a bulk job failure notification email (no job details available)"
    logger.exception(error_text)
    tech_logger.exception(error_text)  # notifies tech support


def _log_bulk_job_statistics():
    """ helper method to log metrics and statistics at the end of the bulk job process """
    if settings.BULK_COURSE_CREATION['log_long_running_jobs']:
        job_age = settings.BULK_COURSE_CREATION['long_running_age_in_minutes']
        job_count = BulkJob.objects.get_long_running_jobs(older_than_minutes=job_age)
        if job_count:
            logger.warn("Found %s long-running bulk create jobs (older than %s minutes).", job_count, job_age)
