import logging

from .models import (
    SISCourseData,
    CanvasCourseGenerationJob,
    CanvasSchoolTemplate,
    BulkCanvasCourseCreationJob
)

from .exceptions import (
    NoTemplateExistsForSchool,
    MultipleDefaultTemplatesExistForSchool
)

from icommons_common.models import CourseInstance


logger = logging.getLogger(__name__)


def get_course_data(course_sis_id):
    """
    Returns an instance of the SISCourseData class for the given
    course sis id.  Will raise either an ObjectDoesNotExist exception
    if the id does not map to an instance or a MultipleObjectsReturned
    exception if multiple instances match the input id.
    """
    return SISCourseData.objects.select_related('course').get(pk=course_sis_id)


def get_course_generation_data_for_canvas_course_id(canvas_course_id):
    """
    Retrieve the Canvas course generation job data given the canvas_course_id.
    Returns the first matching record if it exists or None if it does not have
    a job associated.
    """
    result = CanvasCourseGenerationJob.objects.filter(
        canvas_course_id=canvas_course_id
    )
    if len(result) > 0:
        return result[0]
    else:
        return None


def get_course_generation_data_for_sis_course_id(sis_course_id,
                                                 course_job_id=None,
                                                 bulk_job_id=None):
    """
    Retrieve the Canvas course generation job data given the sis_course_id and
    an optional bulk_job_id.
    Returns the first matching record if it exists or None if it  does not have
    a job associated.
    """
    kwargs = {'sis_course_id': sis_course_id, }
    # if there is a job id, there's no need for any other params
    if course_job_id:
        kwargs['pk'] = course_job_id
    else:
        # if there was no job_id, see if there's a bulk_job_id
        # if not, query for bulk_job_id is null
        if bulk_job_id:
            kwargs['bulk_job_id'] = bulk_job_id
        else:
            kwargs['bulk_job_id__isnull'] = True

    try:
        return CanvasCourseGenerationJob.objects.get(**kwargs)
    except (CanvasCourseGenerationJob.DoesNotExist,
            CanvasCourseGenerationJob.MultipleObjectsReturned) as e:
        logger.exception(
            'Unable to find single CanvasCourseGenerationJob for sis_course_id '
            '{}, course_job_id {}, bulk_job_id {}'.format(
                sis_course_id, course_job_id, bulk_job_id))
        return None


def get_default_template_for_school(school_code):
    """
    Find the default CanvasSchoolTemplate for the given school code.  A
    NoTemplateExistsForSchool exception will be raised if the school does not have a template.
    If there are multiple default templates for the school, a MultipleDefaultTemplatesExistForSchool exception
    will be thrown.
    """
    logger.debug("Fetching template for school_code=%s...", school_code)
    query_set = CanvasSchoolTemplate.objects.filter(school_id=school_code)
    # Collect the templates flagged as default
    default_templates = [t for t in query_set if t.is_default]
    if default_templates:
        if len(default_templates) == 1:
            # If we have a default template and there is only one of them, return it
            return default_templates[0]
        else:
            logger.debug("Found multiple default templates for school %s.", school_code)
            raise MultipleDefaultTemplatesExistForSchool(school_code)
    else:
        # There were not any templates flagged as default
        template_count = len(query_set)
        if template_count == 0:
            logger.debug("Did not find a template for school %s.", school_code)
            raise NoTemplateExistsForSchool(school_code)
        elif template_count == 1:
            # If there was only one template, this one is the default
            return query_set[0]
        else:
            logger.debug("Found multiple templates with no default for school %s.", school_code)
            raise MultipleDefaultTemplatesExistForSchool(school_code)


def get_courses_for_term(term_id, is_in_canvas=None, is_in_isite=None, not_created=None):
    """
    Get the count of all the courses in the term. If is_in_canvas is true, only get
    the count of the courses that are already in canvas by looking to see if the sync_to_canvas flag is
    set to true in the course manager database.
    :param term_id: the term_id of the term
    :param is_in_canvas: (optional) if provided the method will only return a count of the courses that already exist in Canvas
    :param is_in_isite: (optional) select courses that have isites
    :param not_created: (optional) select courses with no external site
    :return: The method returns a count of the number of courses, if no courses are found the method will return 0.
    """
    kwargs = { 'term__term_id' : term_id }

    if is_in_canvas:
        kwargs['sync_to_canvas'] = True

    if is_in_isite:
        kwargs['sites__site_type_id'] = 'isite'

    if not_created:
        kwargs['sites__external_id__isnull'] = True

    return CourseInstance.objects.filter(**kwargs).count()


def get_bulk_job_records_for_term(term_id, in_progress=None):
    """
    Get the bulk job records from the BulkCanvasCourseCreationJob table for the sis_term_id.
    if in_progress is true, get only those jobs that have an active status.
    """

    kwargs = { 'sis_term_id' : term_id }
    if in_progress:
        status_list = [BulkCanvasCourseCreationJob.STATUS_SETUP,
                       BulkCanvasCourseCreationJob.STATUS_PENDING,
                       BulkCanvasCourseCreationJob.STATUS_FINALIZING]
        kwargs['status__in'] = status_list

    return BulkCanvasCourseCreationJob.objects.filter(**kwargs)

def select_courses_for_bulk_create(term_id):
    """
    Given a term id, select all course instance id's that are eligible to have a Canvas
    course created. The statement below selects courses where:
        term_id = term_is
        external_id = Null
        site_type_id != 'isite'

    :param term_id:
    :return: List of course instance id's
    """
    select_query = {
        'term_id': term_id,
        'sites__external_id__isnull': True,
        }

    exclude_query = {
        'sites__site_type_id': 'isite',
        }

    return CourseInstance.objects.filter(**select_query)\
        .exclude(**exclude_query).values_list('course_instance_id', flat=True)
