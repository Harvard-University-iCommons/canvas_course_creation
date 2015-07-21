import logging
import json

from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from ims_lti_py.tool_config import ToolConfig

from icommons_common.models import School, Term, Department, CourseGroup, Person
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
    get_term_data,
    get_canvas_site_templates_for_school,
    get_canvas_site_template
)


logger = logging.getLogger(__name__)

COURSE_INSTANCE_FILTERS = ['school', 'term', 'department', 'course_group']


def lti_auth_error(request):
    raise PermissionDenied


@require_http_methods(['GET'])
def tool_config(request):
    env = settings.ENV_NAME if hasattr(settings, 'ENV_NAME') else ''
    url = "%s://%s%s" % (
        request.scheme,
        request.get_host(),
        reverse('bulk_site_creation:lti_launch', exclude_resource_link_id=True)
    )
    lti_tool_config = ToolConfig(
        title="Canvas Site Creator %s" % env,
        launch_url=url,
        secure_launch_url=url,
        description="This LTI tool provides canvas site creation functionality."
    )

    # this is how to tell Canvas that this tool provides an account navigation link:
    lti_tool_config.set_ext_param('canvas.instructure.com', 'account_navigation', {
        'enabled': 'true',
        'text': "Canvas Site Creator %s" % env
    })
    lti_tool_config.set_ext_param('canvas.instructure.com', 'privacy_level', 'public')

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml', status=200)


@login_required
@require_http_methods(['POST'])
@csrf_exempt
def lti_launch(request):
    logger.debug("bulk_site_creation launched with params: %s", json.dumps(request.POST.dict(), indent=4))
    return redirect('bulk_site_creation:index')


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def index(request):
    canvas_user_id = request.LTI['custom_canvas_user_id']
    sis_account_id = request.LTI['custom_canvas_account_sis_id']
    ci_filters = {key: request.GET.get(key, '') for key in COURSE_INSTANCE_FILTERS}
    (account_type, _) = canvas_api_accounts.parse_canvas_account_id(sis_account_id)
    schools = []
    terms = []
    departments = []
    course_groups = []
    school = None

    if account_type in canvas_api_accounts.ACCOUNT_TYPES:
        # We are in the context of a SIS type account, so limit options to that context
        school_id = sis_account_id
        if account_type == canvas_api_accounts.ACCOUNT_TYPE_DEPARTMENT:
            department = canvas_api_accounts.get_account_by_sis_account_id(canvas_user_id, sis_account_id)
            department_id = department['sis_account_id']
            school_id = department['parent_account_id']
            ci_filters[canvas_api_accounts.ACCOUNT_TYPE_COURSE_GROUP] = department_id
            departments.append(get_department_data_for_school(canvas_user_id, school_id, department_id))
        elif account_type == canvas_api_accounts.ACCOUNT_TYPE_COURSE_GROUP:
            course_group = canvas_api_accounts.get_account_by_sis_account_id(canvas_user_id, sis_account_id)
            course_group_id = course_group['sis_account_id']
            school_id = course_group['parent_account_id']
            ci_filters[canvas_api_accounts.ACCOUNT_TYPE_COURSE_GROUP] = course_group_id
            course_groups.append(get_course_group_data_for_school(canvas_user_id, school_id, course_group_id))
        school = get_school_data_for_user(canvas_user_id, school_id)
        ci_filters[canvas_api_accounts.ACCOUNT_TYPE_SCHOOL] = school['id']
        schools.append(school)
    else:
        # We are outside the context of a SIS type account, so show all schools
        # that the user has permission to create courses for
        schools = get_school_data_for_user(canvas_user_id)
        school_sis_account_id = ci_filters.get('school')
        if school_sis_account_id:
            school = get_school_data_for_user(canvas_user_id, school_sis_account_id)

    if len(schools) == 0:
        return redirect('not_authorized')

    if school:
        # Populate term, department, and course_group filter options if we already have a school
        school_sis_account_id = school['id']
        terms = get_term_data_for_school(school_sis_account_id)
        if not departments and not course_groups:
            departments = get_department_data_for_school(canvas_user_id, school_sis_account_id)
            course_groups = get_course_group_data_for_school(canvas_user_id, school_sis_account_id)

    return render(request, 'bulk_site_creation/index.html', {
        'filters': ci_filters,
        'schools': schools,
        'terms': terms,
        'departments': departments,
        'course_groups': course_groups
    })


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def audit(request):
    canvas_user_id = request.LTI['custom_canvas_user_id']
    sis_account_id = request.LTI['custom_canvas_account_sis_id']
    (account_type, account_id) = canvas_api_accounts.parse_canvas_account_id(sis_account_id)

    filter_kwargs = {}
    if account_type == canvas_api_accounts.ACCOUNT_TYPE_SCHOOL:
        filter_kwargs['school_id'] = account_id
    elif account_type == canvas_api_accounts.ACCOUNT_TYPE_DEPARTMENT:
        filter_kwargs['sis_department_id'] = account_id
    elif account_type == canvas_api_accounts.ACCOUNT_TYPE_COURSE_GROUP:
        filter_kwargs['sis_course_group_id'] = account_id

    query_set = BulkCanvasCourseCreationJob.objects.filter(**filter_kwargs).order_by('-created_at')

    jobs = []
    creator_ids = set()
    school_ids = set()
    term_ids = set()
    department_ids = set()
    course_group_ids = set()
    for bulk_job in query_set:
        jobs.append(bulk_job)
        creator_ids.add(bulk_job.created_by_user_id)
        school_ids.add(bulk_job.school_id)
        term_ids.add(bulk_job.sis_term_id)
        if bulk_job.sis_department_id:
            department_ids.add(bulk_job.sis_department_id)
        if bulk_job.sis_course_group_id:
            course_group_ids.add(bulk_job.sis_course_group_id)

    creators = {p.univ_id: p for p in Person.objects.filter(univ_id__in=creator_ids)}
    schools = School.objects.in_bulk(school_ids)
    terms = Term.objects.in_bulk(term_ids)
    departments = {}
    if department_ids:
        departments = {
            id: name for id, name in Department.objects.filter(
                department_id__in=department_ids
            ).values_list('department_id', 'name')
        }
    course_groups = {}
    if course_group_ids:
        course_groups = {
            id: name for id, name in CourseGroup.objects.filter(
                course_group_id__in=course_group_ids
            ).values_list('course_group_id', 'name')
        }

    bulk_job_data = []
    for bulk_job in jobs:
        try:
            creator = creators[bulk_job.created_by_user_id]
            creator_name = "%s, %s" % (creator.name_last, creator.name_first)
        except KeyError:
            # Bulk job creator could not be found
            logger.warning("Failed to find bulk canvas site job creator %s", bulk_job.created_by_user_id)
            creator_name = ''

        school = schools[bulk_job.school_id]
        term = terms[bulk_job.sis_term_id]
        department = ''
        if bulk_job.sis_department_id:
            department = departments[bulk_job.sis_department_id]
        course_group = ''
        if bulk_job.sis_course_group_id:
            course_group = course_groups[bulk_job.sis_course_group_id]
        template_canvas_course = get_canvas_site_template(school.school_id, bulk_job.template_canvas_course_id)

        bulk_job_data.append({
            'id': bulk_job.id,
            'created_at': timezone.localtime(bulk_job.created_at).strftime('%b %d, %Y %H:%M:%S'),
            'status': bulk_job.status_display_name,
            'created_by': creator_name,
            'term': term.display_name,
            'school': school.title_short,
            'subaccount': department if department else course_group,
            'template_canvas_course': template_canvas_course,
            'count_course_jobs': CanvasCourseGenerationJob.objects.filter(bulk_job_id=bulk_job.id).count()
        })

    return render(request, 'bulk_site_creation/audit.html', {
        'bulk_job_data': bulk_job_data
    })


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def course_selection(request):
    canvas_user_id = request.LTI['custom_canvas_user_id']
    ci_filters = {key: request.GET.get(key, '') for key in COURSE_INSTANCE_FILTERS}

    try:
        school = get_school_data_for_user(canvas_user_id, ci_filters['school'])
        term = get_term_data(ci_filters['term'])
    except KeyError:
        redirect('bulk_site_creation:index')

    (account_type, school_id) = canvas_api_accounts.parse_canvas_account_id(school['id'])
    canvas_site_templates = get_canvas_site_templates_for_school(school_id)

    account = school
    department = {}
    if ci_filters['department']:
        department = get_department_data_for_school(canvas_user_id, school['id'], ci_filters['department'])
        account = department
    course_group = {}
    if ci_filters['course_group']:
        course_group = get_course_group_data_for_school(canvas_user_id, school['id'], ci_filters['course_group'])
        account = course_group

    ci_query_set = get_course_instance_query_set(term['id'], account['id'])
    course_instance_summary = get_course_instance_summary_data(ci_query_set)

    return render(request, 'bulk_site_creation/course_selection.html', {
        'filters': ci_filters,
        'school': school,
        'term': term,
        'department': department,
        'course_group': course_group,
        'canvas_site_templates': canvas_site_templates,
        'course_instance_summary': course_instance_summary
    })


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['POST'])
def create_job(request):
    canvas_user_id = request.LTI['custom_canvas_user_id']
    logged_in_user_id = request.LTI['lis_person_sourcedid']
    data = json.loads(request.POST['data'])

    template_canvas_course_id = data.get('template')
    filters = data['filters']
    term = filters.get('term')

    school_account_id = filters['school']
    account_id = school_account_id
    (account_type, school_id) = canvas_api_accounts.parse_canvas_account_id(school_account_id)

    department = None
    department_account_id = filters.get('department')
    if department_account_id:
        account_id = department_account_id
        (account_type, department) = department_account_id.split(':')

    course_group = None
    course_group_account_id = filters.get('course_group')
    if course_group_account_id:
        account_id = course_group_account_id
        (account_type, course_group) = course_group_account_id.split(':')

    # Check permissions for selected account
    if not canvas_api_accounts.has_permission(
            canvas_user_id, account_id, canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES):
        logger.info(
            'Failed to create bulk job for user %s and account %s: Missing %s permission',
            canvas_user_id,
            account_id,
            canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES
        )
        raise PermissionDenied

    created_by_user_id = logged_in_user_id
    if not created_by_user_id:
        created_by_user_id = "canvas_user_id:%s" % canvas_user_id

    create_bulk_job_kwargs = {
        'school_id': school_id,
        'sis_term_id': int(term),
        'sis_department_id': int(department) if department else None,
        'sis_course_group_id': int(course_group) if course_group else None,
        'template_canvas_course_id': template_canvas_course_id,
        'created_by_user_id': created_by_user_id,
        'course_instance_ids': data['course_instance_ids']
    }

    bulk_job = BulkCanvasCourseCreationJob.objects.create_bulk_job(**create_bulk_job_kwargs)

    return redirect('bulk_site_creation:bulk_job_detail', bulk_job.id)


@login_required
@has_account_permission(canvas_api_accounts.ACCOUNT_PERMISSION_MANAGE_COURSES)
@require_http_methods(['GET'])
def bulk_job_detail(request, bulk_job_id):
    bulk_job = BulkCanvasCourseCreationJob.objects.get(id=bulk_job_id)
    bulk_job_complete = bulk_job.status in (
        BulkCanvasCourseCreationJob.STATUS_NOTIFICATION_SUCCESSFUL,
        BulkCanvasCourseCreationJob.STATUS_NOTIFICATION_FAILED
    )
    course_job_summary = get_course_job_summary_data(bulk_job.id)

    school = School.objects.get(school_id=bulk_job.school_id)
    term = Term.objects.get(term_id=bulk_job.sis_term_id)

    department = None
    if bulk_job.sis_department_id:
        department = Department.objects.get(department_id=bulk_job.sis_department_id).name

    course_group = None
    if bulk_job.sis_course_group_id:
        course_group = CourseGroup.objects.get(course_group_id=bulk_job.sis_course_group_id).name

    template = get_canvas_site_template(school.school_id, bulk_job.template_canvas_course_id)

    return render(request, 'bulk_site_creation/bulk_job_detail.html', {
        'bulk_job': bulk_job,
        'bulk_job_complete': bulk_job_complete,
        'school': school.title_short,
        'term': term.display_name,
        'department': department,
        'course_group': course_group,
        'template': template,
        'course_jobs_total': course_job_summary['recordsTotal'],
        'course_jobs_complete': course_job_summary['recordsComplete'],
        'course_jobs_successful': course_job_summary['recordsSuccessful'],
        'course_jobs_failed': course_job_summary['recordsFailed']
    })
