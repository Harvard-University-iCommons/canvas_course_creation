import logging
import json

from django.conf import settings
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from icommons_common.models import CourseInstance, School, Term, Department, CourseGroup, Person
from icommons_common.view_utils import create_json_200_response, create_json_500_response
from icommons_common.canvas_api.helpers import accounts as canvas_api_accounts
from icommons_common.auth.lti_decorators import has_account_permission

from canvas_course_site_wizard.models import BulkCanvasCourseCreationJob, CanvasCourseGenerationJob

from .models import (
    get_course_instance_query_set,
    get_course_instance_summary_data,
    get_course_job_summary_data
)
from .utils import (
    get_school_data_for_user,
    get_term_data_for_school,
    get_department_data_for_school,
    get_course_group_data_for_school,
)

logger = logging.getLogger(__name__)

COURSE_INSTANCE_DATA_FIELDS = ('course_instance_id', 'course_instance_id', 'course__registrar_code_display', 'title')
BULK_JOB_DATA_FIELDS = ('created_at', 'status')
COURSE_JOB_DATA_FIELDS = ('created_at', 'workflow_state')


def _unpack_datatables_params(request):
    return (
        int(request.GET.get('draw', 0)),
        int(request.GET.get('start', 0)),
        int(request.GET.get('length', 10)),
        int(request.GET.get('order[0][column]', 3)),
        request.GET.get('order[0][dir]', 'asc'),
        request.GET.get('search[value]')
    )


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def course_jobs(request, bulk_job_id):
    """
    Searches for individual course creation jobs using the GET parameters given

    :param request:
    :return: JSON response containing the list of individual course creation jobs
    """
    result = {}
    try:
        (draw, start, limit, sort_index, sort_dir, search) = _unpack_datatables_params(request)

        order_by_operator = '-' if sort_dir == 'desc' else ''
        query_set_all = CanvasCourseGenerationJob.objects.filter(bulk_job_id=bulk_job_id).order_by(
            order_by_operator + COURSE_JOB_DATA_FIELDS[sort_index]
        )

        result.update(get_course_job_summary_data(bulk_job_id))
        result['draw'] = draw

        jobs = []
        creator_ids = []
        course_instance_ids = []
        for course_job in query_set_all[start:(start + limit)]:
            jobs.append(course_job)
            creator_ids.append(course_job.created_by_user_id)
            course_instance_ids.append(course_job.sis_course_id)

        creators = {p.univ_id: p for p in Person.objects.filter(univ_id__in=creator_ids)}
        course_instances = {
            str(ci.course_instance_id): ci for ci in CourseInstance.objects.filter(
                course_instance_id__in=course_instance_ids
            )
        }

        data = []
        for job in jobs:
            try:
                creator = creators[job.created_by_user_id]
                creator_name = "%s, %s" % (creator.name_last, creator.name_first)
            except KeyError:
                # Course job creator could not be found
                logger.warning("Failed to find canvas course site job creator %s", job.created_by_user_id)
                creator_name = ''
            course_instance = course_instances[job.sis_course_id]

            data.append({
                'id': job.id,
                'created_at': timezone.localtime(job.created_at).strftime('%b %d, %Y %H:%M:%S'),
                'status': job.status_display_name,
                'created_by': creator_name,
                'sis_course_id': job.sis_course_id,
                'registrar_code': course_instance.course.registrar_code_display,
                'course_title': course_instance.title,
                'canvas_course_id': job.canvas_course_id
            })
        result['data'] = data
    except Exception:
        logger.exception(
            "Failed to get course jobs with LTI params %s and GET params %s",
            json.dumps(request.LTI),
            json.dumps(request.GET)
        )
        result['error'] = 'There was a problem searching for course jobs. Please try again.'
        return create_json_500_response(result)

    return create_json_200_response(result)


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def schools(request):
    """
    Gets the list of schools that the current user has permission to manage

    :param request:
    :return: JSON response containing the list of schools
    """
    try:
        data = get_school_data_for_user(request.LTI['custom_canvas_user_id'])
        return create_json_200_response(data)
    except Exception:
        message = "Failed to get schools with LTI params %s" % json.dumps(request.LTI)
        logger.exception(message)
        return create_json_500_response(message)


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def terms(request, sis_account_id):
    """
    Gets the list of terms for a given school

    :param request:
    :param sis_account_id: The sis_account_id for which to find terms
    :return: JSON response containing the list of terms
    """
    try:
        data = get_term_data_for_school(sis_account_id)
        return create_json_200_response(data)
    except Exception:
        message = "Failed to get terms with LTI params %s" % json.dumps(request.LTI)
        logger.exception(message)
        return create_json_500_response(message)


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def departments(request, sis_account_id):
    """
    Gets the list of departments that the current user has permission to manage

    :param request:
    :param sis_account_id: The sis_account_id for which to find departments
    :return: JSON response containing the list of departments
    """
    try:
        data = get_department_data_for_school(request.LTI['custom_canvas_user_id'], sis_account_id)
        return create_json_200_response(data)
    except Exception:
        message = "Failed to get departments with LTI params %s" % json.dumps(request.LTI)
        logger.exception(message)
        return create_json_500_response(message)


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def course_groups(request, sis_account_id):
    """
    Gets the list of course_groups that the current user has permission to manage

    :param request:
    :param sis_account_id: The sis_account_id for which to find course_groups
    :return: JSON response containing the list of course_groups
    """
    try:
        data = get_course_group_data_for_school(request.LTI['custom_canvas_user_id'], sis_account_id)
        return create_json_200_response(data)
    except Exception:
        message = "Failed to get course_groups with LTI params %s" % json.dumps(request.LTI)
        logger.exception(message)
        return create_json_500_response(message)


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def course_instances(request, sis_term_id, sis_account_id):
    """
    Searches for course instances using the GET parameters given

    :param request:
    :param sis_term_id: The SIS term to find course instances for
    :param sis_account_id: The Canvas account ID for the school to find course instances for
    :return: JSON response containing the list of course instances
    """
    result = {}
    try:
        (draw, start, limit, sort_index, sort_dir, search) = _unpack_datatables_params(request)

        query_set = get_course_instance_query_set(sis_term_id, sis_account_id)
        query_set = query_set.select_related('course')
        # Added prefetch_related here to reduce hitting the database again later
        # when we query for the associated iSites.
        query_set = query_set.prefetch_related('sites')

        # Apply text search filter
        if search:
            query_set = query_set.filter(
                Q(course__registrar_code__icontains=search) |
                Q(course__registrar_code_display__icontains=search) |
                Q(title__icontains=search)
            )

        order_by_operator = '-' if sort_dir == 'desc' else ''
        query_set = query_set.order_by(order_by_operator + COURSE_INSTANCE_DATA_FIELDS[sort_index])

        # fixes TLT-1570 where courses that already have a Canvas course were showing up
        # in the create list
        query_set = query_set.exclude(canvas_course_id__isnull=False)

        result = get_course_instance_summary_data(query_set)

        data = []
        for ci in query_set[start:(start + limit)]:
            # Get associated iSites keywords and external URL if present(TLT-1578)
            sites = [site.external_id for site in ci.sites.all() if site.site_type_id in ['isite', 'external']]
            official = [site_map.map_type_id for site_map in ci.sitemap_set.all()]
            data.append({
                'id': ci.course_instance_id,
                'registrar_code': ci.course.registrar_code_display,
                'title': ci.title,
                'has_canvas_site': ci.canvas_course_id is not None,
                'associated_sites': ', '.join(sites),
                'site_status': ', '.join(official),
            })

        result['data'] = data
        result['draw'] = draw
    except Exception:
        logger.exception(
            "Failed to get course_instances with LTI params %s and GET params %s",
            json.dumps(request.LTI),
            json.dumps(request.GET)
        )
        result['error'] = 'There was a problem searching for courses. Please try again.'
        return create_json_500_response(result)

    return create_json_200_response(result)


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def course_instance_summary(request, sis_term_id, sis_account_id):
    """
    Return counts of course instances using the GET parameters given

    :param request:
    :param sis_term_id: The SIS term to count course instances for
    :param sis_account_id: The Canvas account ID for the school to count course instances for
    :return: JSON response containing the course instance counts
    """
    result = {}
    try:
        query_set = get_course_instance_query_set(sis_term_id, sis_account_id)
        result = get_course_instance_summary_data(query_set)
    except Exception:
        logger.exception(
            "Failed to get course_instance_summary with LTI params %s and GET params %s",
            json.dumps(request.LTI),
            json.dumps(request.GET)
        )
        result['error'] = 'There was a problem counting courses. Please try again.'
        return create_json_500_response(result)

    return create_json_200_response(result)
