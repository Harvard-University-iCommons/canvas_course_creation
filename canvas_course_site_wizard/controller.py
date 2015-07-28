import logging

from canvas_sdk.methods.courses import create_new_course, get_single_course_courses, update_course
from canvas_sdk.methods.sections import create_course_section
from canvas_sdk.methods.enrollments import enroll_user_sections
from canvas_sdk.methods.users import get_user_profile
from canvas_sdk.methods import content_migrations
from canvas_sdk.exceptions import CanvasAPIError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.core.mail import send_mail

from .models_api import (
    get_course_data,
    get_default_template_for_school,
    get_courses_for_term,
    get_bulk_job_records_for_term,
    select_courses_for_bulk_create,
    get_course_generation_data_for_sis_course_id
)
from .models import (
    CanvasCourseGenerationJob,
    SISCourseData,
    BulkCanvasCourseCreationJob,
    CanvasSchoolTemplate
)
from icommons_common.models import (
    CourseStaff,
    UserRole,
    CourseInstance
)

from .exceptions import (
    CanvasCourseAlreadyExistsError,
    CanvasCourseCreateError,
    CanvasEnrollmentError,
    CanvasSectionCreateError,
    CopySISEnrollmentsError,
    CourseGenerationJobCreationError,
    CourseGenerationJobNotFoundError,
    MarkOfficialError,
    NoCanvasUserToEnroll,
    NoTemplateExistsForSchool,
    SISCourseDoesNotExistError,
    SaveCanvasCourseIdToCourseGenerationJobError,
    SaveCanvasCourseIdToCourseInstanceError,
)
from icommons_common.canvas_utils import SessionInactivityExpirationRC


# Set up the request context that will be used for canvas API calls
SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)
logger = logging.getLogger(__name__)


def create_canvas_course(sis_course_id, sis_user_id, bulk_job=None):
    """
    This method creates a canvas course for the sis_course_id provided, initiated by the sis_user_id. The bulk_job_id
    would be passed in if it's invoked from a bulk feed process.
    """

    # instantiate any variables required for method return or logger calls
    new_course = None
    section = None
    course_job_id = None

    # 1. Insert a CanvasCourseGenerationJob record on initiation with STATUS_SETUP status. This would  help in
    # keeping track of the status of the various courses in the bulk job context as well as general reporting

    # if there's no bulk id, we need to create the CanvasCourseGenerationJob
    bulk_job_id = None
    template_id = None
    if bulk_job:
        bulk_job_id = bulk_job.id
        template_id = bulk_job.template_canvas_course_id
        try:
            course_generation_job = CanvasCourseGenerationJob.objects.filter(
                                        sis_course_id=sis_course_id,
                                        bulk_job_id=bulk_job_id).get()
        except Exception as e:
            ex = CourseGenerationJobNotFoundError(msg_details=(bulk_job_id,
                                                               sis_course_id))
            logger.exception(ex.display_text)
            raise ex
    else:
        try:
            logger.debug('Create content migration job tracking row...')
            course_generation_job = CanvasCourseGenerationJob.objects.create(
                sis_course_id=sis_course_id,
                created_by_user_id=sis_user_id,
                workflow_state=CanvasCourseGenerationJob.STATUS_SETUP,
            )
            course_job_id = course_generation_job.pk
            logger.debug('Job row created: %s' % course_generation_job)
        except Exception as e:
            logger.exception('Error  in inserting CanvasCourseGenerationJob record for '
                             'with sis_course_id=%s: exception=%s' % (sis_course_id, e))

            # send email in addition to showing error page to user
            ex = CourseGenerationJobCreationError(msg_details=sis_course_id)
            send_failure_msg_to_support(sis_course_id, sis_user_id, ex.display_text)
            raise ex

    try:
        # 2. fetch the course instance info
        course_data = get_course_data(sis_course_id)
        logger.info("\n obtained course info for ci=%s, acct_id=%s, course_name=%s, code=%s, term=%s, section_name=%s\n"
                    % (course_data, course_data.sis_account_id, course_data.course_name, course_data.course_code,
                       course_data.sis_term_id, course_data.primary_section_name()))
    except ObjectDoesNotExist as e:
        logger.error('ObjectDoesNotExist exception when fetching SIS data for course '
                     'with sis_course_id=%s: exception=%s' % (sis_course_id, e))
        # Update the status to STATUS_SETUP_FAILED on any failures
        update_course_generation_workflow_state(
            sis_course_id, CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
            course_job_id=course_job_id, bulk_job_id=bulk_job_id)

        ex = SISCourseDoesNotExistError(sis_course_id)
        # If the course is part of bulk job, do not send individual email. .
        if not bulk_job_id:
            msg = ex.display_text
            # TLT-393: send an email to support group, in addition to showing error page to user
            send_failure_msg_to_support(sis_course_id, sis_user_id, msg)
        raise ex

    # 3. Attempt to create a canvas course
    request_parameters = dict(
        request_ctx=SDK_CONTEXT,
        account_id='sis_account_id:%s' % course_data.sis_account_id,
        course_name=course_data.course_name,
        course_course_code=course_data.course_code,
        course_term_id='sis_term_id:%s' % course_data.sis_term_id,
        course_sis_course_id=sis_course_id,
        course_is_public_to_auth_users=course_data.shopping_active
    )

    # If this was not part of a bulk job, attempt to get the default template for the given school
    if not bulk_job_id:
        try:
            template_id = get_default_template_for_school(course_data.school_code).template_id
        except NoTemplateExistsForSchool:
            # No template exists for the school, so no need to copy visibility settings
            pass

    # If creating from a template, get template course, so visibility settings
    # can be copied over to the new course
    if template_id:
        try:
            template_course = get_single_course_courses(SDK_CONTEXT, template_id, 'all_courses').json()
            is_public_to_auth_users = course_data.shopping_active or template_course['is_public_to_auth_users']
            # Update create course request parameters
            request_parameters.update({
                'course_is_public': template_course['is_public'],
                'course_public_syllabus': template_course['public_syllabus'],
                'course_is_public_to_auth_users': is_public_to_auth_users
            })
        except CanvasAPIError:
            logger.exception(
                'Failed to retrieve template course %d for creation of site for course instance %s in account %s',
                template_id,
                sis_course_id,
                course_data.sis_account_id
            )
            # Update the status to STATUS_SETUP_FAILED on failure to retrieve template course
            update_course_generation_workflow_state(
                sis_course_id,
                CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
                course_job_id=course_generation_job.id,
                bulk_job_id=bulk_job_id
            )
            ex = CanvasCourseCreateError(msg_details=sis_course_id)
            if not bulk_job_id:
                send_failure_msg_to_support(sis_course_id, sis_user_id, ex.display_text)
            raise ex

    try:
        new_course = create_new_course(**request_parameters).json()
    except CanvasAPIError as api_error:
        logger.exception(
            'Error building request_parameters or executing create_new_course() '
            'SDK call for new Canvas course with request=%s:',
            request_parameters)
        # Update the status to STATUS_SETUP_FAILED on any failures
        update_course_generation_workflow_state(sis_course_id,
            CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
            course_job_id=course_job_id, bulk_job_id=bulk_job_id)

        # a 400 errors here means that the SIS id already exists in Canvas
        if api_error.status_code == 400:
            raise CanvasCourseAlreadyExistsError(msg_details=sis_course_id)

        ex = CanvasCourseCreateError(msg_details=sis_course_id)
        if not bulk_job_id:
            send_failure_msg_to_support(sis_course_id, sis_user_id, ex.display_text)
        raise ex

    logger.info("created course object, ret=%s" % new_course)

    # 4. Save the canvas course id to the generation job
    course_generation_job.canvas_course_id = new_course['id']
    try:
        course_generation_job.save(update_fields=['canvas_course_id'])
    except Exception as e:
        # Update the status to STATUS_SETUP_FAILED on any failures
        update_course_generation_workflow_state(sis_course_id,
            CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
            course_job_id=course_job_id, bulk_job_id=bulk_job_id)
        ex = SaveCanvasCourseIdToCourseGenerationJobError(
                msg_details=(new_course['id'], course_generation_job.pk))
        logging.exception(ex.display_text)
        if not bulk_job_id:
            send_failure_msg_to_support(sis_course_id, sis_user_id,
                                        ex.display_text)
        raise ex

    # 5. Save the canvas course id to the course instance
    course_data.canvas_course_id = new_course['id']
    try:
        course_data.save(update_fields=['canvas_course_id'])
    except Exception as e:
        # Update the status to STATUS_SETUP_FAILED on any failures
        update_course_generation_workflow_state(sis_course_id,
            CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
            course_job_id=course_job_id, bulk_job_id=bulk_job_id)
        ex = SaveCanvasCourseIdToCourseInstanceError(
                msg_details=(new_course['id'], course_data.pk))
        logging.exception(ex.display_text)
        if not bulk_job_id:
            send_failure_msg_to_support(sis_course_id, sis_user_id,
                                        ex.display_text)
        raise ex

    # 6. Create course section after course creation
    try:
        request_parameters = dict(request_ctx=SDK_CONTEXT,
                                  course_id=new_course['id'],
                                  course_section_name=course_data.primary_section_name(),
                                  course_section_sis_section_id=sis_course_id)
        section = create_course_section(**request_parameters).json()
        logger.info("created section= %s" % section)
    except CanvasAPIError as e:
        logger.exception(
            'Error building request_parameters or executing '
            'create_course_section() SDK call for new Canvas course id=%s with '
            'request=%s' % (new_course.get('id', '<no ID>'),
                            request_parameters))

        # Update the status to STATUS_SETUP_FAILED on any failures
        update_course_generation_workflow_state(sis_course_id,
            CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
            course_job_id=course_job_id, bulk_job_id=bulk_job_id)

        # send email in addition to showing error page to user
        ex = CanvasSectionCreateError(msg_details=sis_course_id)
        if not bulk_job_id:
            send_failure_msg_to_support(sis_course_id, sis_user_id, ex.display_text)
        raise ex

    # if this creation is part of a single course creation process return
    # the course along with the new job_id. The start_course_template_copy method will updated
    # the worng record if job id is no supplied.
    if course_job_id:
        return new_course, course_job_id

    return new_course


def start_course_template_copy(sis_course, canvas_course_id, user_id, course_job_id=None,
                               bulk_job_id=None, template_id=None):
    """
    This method will retrieve the template site associated with an SISCourseData object and start the
    Canvas process of copying the template content into the canvas course site.  A CanvasCourseGenerationJob
    row will be created with the async process data from Canvas and the resulting data object will be
    returned.  If the school associated with the sis data object does not have a template, a
    NoTemplateExistsForSchool exception will be raised.
    Based on the bulk_jb_id being passed, the copy process will handle singletons differently from bulk
    course creation in terms of email generation, etc.
    """

    school_code = sis_course.school_code
    if not template_id:
        # If a template was not given, see if there is a default template for the school
        template_id = get_default_template_for_school(school_code).template_id

    course_generation_job = get_course_generation_data_for_sis_course_id(
        sis_course.pk,
        course_job_id=course_job_id,
        bulk_job_id=bulk_job_id
    )

    # Initiate course copy for template_id
    logger.debug('Requesting content migration from Canvas for canvas_course_id=%s...' % canvas_course_id)
    content_migration = content_migrations.create_content_migration_courses(
        SDK_CONTEXT,
        canvas_course_id,
        migration_type='course_copy_importer',
        settings_source_course_id=template_id,
    ).json()
    logger.debug('content migration API call result: %s' % content_migration)

    #  Update the status of   course generation job  with metadata (canvas id, workflow_state, progress url, etc)
    logger.debug('Update course generation job tracking row...')

    course_generation_job.canvas_course_id = canvas_course_id
    course_generation_job.content_migration_id = content_migration['id']
    course_generation_job.workflow_state = CanvasCourseGenerationJob.STATUS_QUEUED
    course_generation_job.status_url = content_migration['progress_url']
    course_generation_job.created_by_user_id = user_id

    course_generation_job.save(update_fields=['canvas_course_id', 'content_migration_id', 'status_url', 'workflow_state',
                                      'created_by_user_id'])

    logger.debug('Job row updated: %s' % course_generation_job)

    return course_generation_job


def finalize_new_canvas_course(canvas_course_id, sis_course_id, user_id, bulk_job_id=None):
    """
    Performs all synchronous tasks required to initialize a new canvas course after the course template
    has been applied, or after checking for a template if the course has no template.

        :param canvas_course_id: newly created Canvas course ID; used to build course URL
        :type canvas_course_id: string
        :param sis_course_id: newly created Canvas course SIS ID; used to enroll course creator
        :type sis_course_id: string
        :param user_id: The user ID of the creator/instructor to enroll in the course; this should be
        either the Canvas user ID or the SIS user ID prepended with the string 'sis_user_id:'
        :type user_id: string
        :param bulk_job_id: The bulk_job_id of the of the course, if it is part of bulk job creation, else None
        :type bulk_job_id: int
        :raises: Logs and re-raises various exceptions raised by its component processes
    """

    """
    Enroll instructor/creator if this is a single course creation, but not if it is part of bulk job
    creation.(TLT-1132)
    """
    if not bulk_job_id:
        try:
            enrollment = enroll_creator_in_new_course(sis_course_id, user_id)
            logger.info('Enrolled user_id=%s in new course with Canvas course id=%s', user_id, canvas_course_id)
            logger.debug("enrollment result: %s", enrollment)
        except Exception as e:
            logger.exception('Error enrolling course creator with user_id=%s in new course with Canvas course id=%s:',
                             user_id, canvas_course_id)
            raise CanvasEnrollmentError(sis_course_id)

    # Copy SIS enrollments to new Canvas course
    try:
        sis_course_data = get_course_data(sis_course_id)
        logger.debug("sis_course_data=%s" % sis_course_data)
        sis_course_data = sis_course_data.set_sync_to_canvas(SISCourseData.TURN_ON_SYNC_TO_CANVAS)
        logger.info('Set SIS enrollment data sync flag for new course with Canvas ID=%s' % canvas_course_id)
        logger.debug("sis_course_data after sync to canvas: %s" % sis_course_data)
    except Exception as e:
        logger.exception('Error setting SIS enrollment data sync flag for new course with Canvas ID=%s:'
                         % canvas_course_id)
        raise CopySISEnrollmentsError(sis_course_id)

    # Mark course as official
    try:
        canvas_course_url = get_canvas_course_url(canvas_course_id=canvas_course_id)
        site_map = sis_course_data.set_official_course_site_url(canvas_course_url)
        logger.info('Marked new course with Canvas ID=%s as official' % canvas_course_id)
        logger.debug("site_map: %s" % site_map)
    except Exception as e:
        logger.exception('Error marking new course with Canvas ID=%s as official:' % canvas_course_id)
        raise MarkOfficialError(sis_course_id)

    logger.info("All tasks for finalizing new course with Canvas ID=%s completed." % canvas_course_id)

    return canvas_course_url

def enroll_creator_in_new_course(sis_course_id, user_id):
    """
    Silently enroll instructor / creator to the new course so it can be accessed immediately

        :param sis_course_id: newly created Canvas course's SIS course ID to enroll course creator
        :type sis_course_id: string
        :param user_id: The user ID of the creator/instructor to enroll in the course
        :type user_id: string - Canvas user ID or SIS user ID prefixed with 'sis_user_id:'
        :return: Canvas enrollment information (response of enrollment request)
        :rtype: json-encoded content of response
        :raises: NoCanvasUserToEnroll
    """

    # check if user exists in Canvas before enrolling
    logger.debug("Checking for user_id=%s" % user_id)

    get_user_response = get_user_profile(request_ctx=SDK_CONTEXT, user_id=user_id)

    logger.debug("--> response: %s" % get_user_response.json())

    if get_user_response.status_code == 200:
        # user was found; we may have found user using sis_user_id, so make sure we note canvas_user_id from response
        user_data = get_user_response.json()
        canvas_user_id = str(user_data['id'])
        sis_user_id = str(user_data['sis_user_id'])
    else:
        # Could not find user matching sis_user_id
        logger.debug("No user found with user_id=%s" % user_id)
        raise NoCanvasUserToEnroll(user_id)

    # Assumptions:
    # 1. the course creator should be enrolled in a section with sis_section_id equal to the SIS course ID
    # 2. the course creator should be enrolled according to the the registrar's feed recorded in CourseManger.
    #  default to Teacher if a role is not found

    enrollment_type = 'TeacherEnrollment'

    # Check for the specific  role from the course staff table
    try:
        user_staff_record = CourseStaff.objects.get(
            course_instance_id=sis_course_id,
            user_id=sis_user_id)
        role_id = user_staff_record.role_id
        logger.debug('CourseStaff role_id =%s' % role_id)

        # Fetch the canvas role information from user role table.
        enrollment_role_record = UserRole.objects.get(role_id=role_id)
        enrollment_role = enrollment_role_record.canvas_role
        logger.info('Attempting to add user to course with role=%s ' % enrollment_role)

        current_user_enrollment_result = enroll_user_sections(request_ctx=SDK_CONTEXT,
                                                              section_id='sis_section_id:%s' % sis_course_id,
                                                              enrollment_user_id=canvas_user_id,
                                                              enrollment_type=enrollment_type,
                                                              enrollment_role=enrollment_role,
                                                              enrollment_enrollment_state='active')

    except Exception as exception:
        logger.exception('Exception in getting custom role information for '
                         'sis_course_id=%s and user_id=%s' % (sis_course_id, sis_user_id))

        # If there is a failure in fetching role information, default to adding the user as Teacher
        current_user_enrollment_result = enroll_user_sections(request_ctx=SDK_CONTEXT,
                                                              section_id='sis_section_id:%s' % sis_course_id,
                                                              enrollment_user_id=canvas_user_id,
                                                              enrollment_type=enrollment_type,
                                                              enrollment_enrollment_state='active')

    logger.debug("Enroll user response: %s" % current_user_enrollment_result.json())
    return current_user_enrollment_result.json()

def get_canvas_user_profile(sis_user_id):
    """
    This method will fetch the canvas user profile , given the sis_user_id
    :param sis_user_id: The sis_user_id of the user, without the sis_user_id: prefix
    :type sis_user_id: string
    return: Returns json representing the canvas user profile fetched by the canvas_sdk
    """
    response = get_user_profile(request_ctx=SDK_CONTEXT, user_id='sis_user_id:%s' % sis_user_id)
    canvas_user_profile = response.json()
    return canvas_user_profile

def send_email_helper(subject, message, to_address):
    """
    This is a helper method to send email using django's mail module. The mail
     is sent to the specified receipients using the subject and body provided.
     The 'from' address is obtained from the settings file.
    :param subject: The subject for the email, a String
    :param message: The body of the email, a String
    :param to_address: The list of recepients, a list of Strings
    """
    from_address = settings.CANVAS_EMAIL_NOTIFICATION['from_email_address']
    logger.info("==>Within send email: from_addr=%s, to_addr=%s, subject=%s, "
                "message=%s" % (from_address, to_address, subject, message))
    # If fail_silently is set to False, send_mail will raise exceptions. If
    # True, all exceptions raised while sending the message will be quashed.
    send_mail(subject, message, from_address, to_address, fail_silently=False)

def send_failure_email(initiator_email, sis_course_id):
    """
    This is a utility to send an email on failure of course migration . It appemds the support email
    to the to_address list and also retrives the necessary subject and body from the settings file.
    Note: It is used  in multiple places and abstracts the details of building the email list and body from the
    calling method
    :param initiator_email: The initiator's email for the message to be sent, a String which can be null if unavailable
    :param sis_course_id: The sis_course_id, so it can be appended to the email details, a String
    """

    to_address = []
    if initiator_email:
        to_address.append(initiator_email)

    # On failure, send message to both initiator and the support group (e.g. icommons-support)
    to_address.append(settings.CANVAS_EMAIL_NOTIFICATION['support_email_address'])
    msg = settings.CANVAS_EMAIL_NOTIFICATION['course_migration_failure_body']
    complete_msg = msg.format(sis_course_id)

    logger.debug(" notifying  failure via email:  to_addr=%s and message=%s"
                 % (to_address, settings.CANVAS_EMAIL_NOTIFICATION['course_migration_failure_body']))
    send_email_helper(settings.CANVAS_EMAIL_NOTIFICATION['course_migration_failure_subject'], complete_msg, to_address)

def send_failure_msg_to_support(sis_course_id, sis_user_id, error_detail):
    """
    This is a utility to send an email to the support group when there is a  failure in course creation . 

    :param sis_course_id: The sis_course_id, so it can be appended to the email details, a String
    :param sis_user_id: The sis_user_id of user  initiating the course creation, a String
    :param error_detail: The error detail that's included in the email, a String 
    """
    to_address = []

    # send message to the support group
    to_address.append(settings.CANVAS_EMAIL_NOTIFICATION['support_email_address'])
    msg = settings.CANVAS_EMAIL_NOTIFICATION['support_email_body_on_failure']
    complete_msg = msg.format(sis_course_id, sis_user_id, error_detail,
                              settings.CANVAS_EMAIL_NOTIFICATION['environment'])
    logger.debug(" send_failure_msg_to_support: sis_course_id=%s, user=%s, complete_msg=%s",
                 sis_course_id, sis_user_id, complete_msg)
    send_email_helper(settings.CANVAS_EMAIL_NOTIFICATION['support_email_subject_on_failure'], complete_msg, to_address)

def get_canvas_course_url(canvas_course_id=None, sis_course_id=None, override_base_url=None):
    """
    This utility method formats a Canvas course URL string which will point to the course home page in Canvas. It
     relies on CANVAS_SITE_SETTINGS['base_url'] as a default. This utility method does not check the validity of the
     input arguments (it will build a string from whatever input it is given, including bad input from settings).

     This method may eventually be in the Canvas Python SDK -- if so, the test should go with it and we might consider
     some argument validation.

    :param canvas_course_id: The ID canvas uses for the course. This will be used if provided, even if sis_course_id
    is also provided; in other words, this value takes precedence over sis_course_id.
    :param sis_course_id: The SIS course ID
    :param override_base_url: The fully qualified base URL for a Canvas server, including http(s)://, domain, and
    trailing forward slash.
    :return: Method returns a URL for a given Canvas course which will point to the course home page in Canvas.
    """

    if canvas_course_id is not None:
        course_id = canvas_course_id
    elif sis_course_id is not None:
        course_id = "sis_course_id:%s" % sis_course_id
    else:
        return None

    if override_base_url is not None:
        base_url = override_base_url
    else:
        base_url = settings.CANVAS_SITE_SETTINGS['base_url']

    course_url = '%scourses/%s' % (base_url, course_id)

    return course_url


def update_course_generation_workflow_state(sis_course_id, workflow_state, course_job_id=None, bulk_job_id=None):
    """
    Update the CanvasCourseGenerationJob record of the sis_course_id with the workflow_state passed in
    :param term_id: The term_id of the term
    :param workflow_state: One of the states from the CanvasCourseGenerationJob's  WORKFLOW_STATUS_CHOICES
    """
    course_job = get_course_generation_data_for_sis_course_id(sis_course_id, course_job_id=course_job_id, bulk_job_id=bulk_job_id)
    if course_job:
        course_job.workflow_state = workflow_state
        course_job.save(update_fields=['workflow_state'])

def update_syllabus_body(course_job):
    # If this was not part of a bulk job, attempt to get the default template for the given school
    canvas_course_id = course_job.canvas_course_id
    course_instance = CourseInstance.objects.get(course_instance_id=int(course_job.sis_course_id))
    school_id = course_instance.course.school_id
    if not course_job.bulk_job_id:
        try:
            template_id = get_default_template_for_school(school_id).template_id
        except NoTemplateExistsForSchool:
            # No template config exists for the school, so skip updating the syllabus body
            return
    else:
        bulk_job = BulkCanvasCourseCreationJob.objects.get(id=course_job.bulk_job_id)
        template_id = bulk_job.template_canvas_course_id

    if template_id:
        try:
            # Populate syllabus body if the school template config indicates that we should do so
            school_template = CanvasSchoolTemplate.objects.get(
                school_id=school_id,
                template_id=template_id
            )
            if school_template.include_course_info:
                update_course(
                    SDK_CONTEXT,
                    canvas_course_id,
                    course_syllabus_body=course_instance.html_formatted_course_info
                )
                logger.info("Updated syllabus body for canvas course course %d", canvas_course_id)
        except (CanvasAPIError, CanvasSchoolTemplate.DoesNotExist, MultipleObjectsReturned):
            logger.exception(
                "Failed to update syllabus body for canvas course %d, course instance %d in school %s",
                canvas_course_id,
                course_instance.course_instance_id,
                school_id
            )
