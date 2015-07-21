import contextlib
import uuid
from unittest import TestCase
from mock import patch, DEFAULT, MagicMock, Mock, ANY

from icommons_ui.exceptions import RenderableException
from django.core.exceptions import ObjectDoesNotExist
from canvas_sdk.exceptions import CanvasAPIError
from canvas_course_site_wizard import controller
from canvas_course_site_wizard.models import (
    CanvasCourseGenerationJob,
    SISCourseData,
)
from canvas_course_site_wizard.exceptions import (
    CanvasCourseAlreadyExistsError,
    CanvasCourseCreateError,
    CanvasSectionCreateError,
    CourseGenerationJobCreationError,
    CourseGenerationJobNotFoundError,
    SISCourseDoesNotExistError,
)


m_canvas_content_generation_job = Mock(
    spec=CanvasCourseGenerationJob,
    id=2,
    canvas_course_id=9999,
    sis_course_id=88323,
    status_url='http://example.com/1234',
    workflow_state='setup',
    created_by_user_id='123'
)
@patch.multiple('canvas_course_site_wizard.controller',
                get_course_data=DEFAULT, create_course_section=DEFAULT,
                create_new_course=DEFAULT)
class CreateCanvasCourseTest(TestCase):
    longMessage = True

    def setUp(self):
        self.bulk_job_id = 10
        self.canvas_course_id = uuid.uuid4().hex
        self.job_id = 1475
        self.sis_course_id = "305841"
        self.sis_user_id = "123456"

    def get_mock_of_get_course_data(self):
        # mock the properties
        course_model_mock = MagicMock(sis_account_id="school:gse",
                                      course_code="GSE",
                                      course_name="GSE test course",
                                      sis_term_id="gse term",
                                      shopping_active=False)
        # mock the methods
        course_model_mock.primary_section_name.return_value = "Primary section"
        return course_model_mock

    # ------------------------------------------------------
    # Tests for create_canvas_course()
    # ------------------------------------------------------

    @patch('canvas_course_site_wizard.controller.create_canvas_course')
    def test_create_canvas_course_method_called_with_right_params(self, create_canvas_course, get_course_data,
                                                                  create_course_section, create_new_course):
        """
        Test that controller makes create_canvas_course call with expected args
        """
        result = create_canvas_course(self.sis_course_id, self.sis_user_id)
        create_canvas_course.assert_called_with(self.sis_course_id, self.sis_user_id)

    # ------------------------------------------------------
    # Tests for create_canvas_course.get_course_data()
    # ------------------------------------------------------

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.create')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    def test_get_course_data_method_called_with_right_params(self,
            course_generation_job__objects__filter, 
            course_generation_job__objects__create, 
            update_course_generation_workflow_state,
            get_course_data, create_course_section, create_new_course):
        """
        Test that controller method makes a call to get_course_data api with expected args
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        course_generation_job__objects__create.return_value = job
        query_set = Mock(get=Mock(return_value=job))
        course_generation_job__objects__filter.return_value = query_set

        controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
        get_course_data.assert_called_with(self.sis_course_id)

    @patch('canvas_course_site_wizard.controller.logger')
    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_object_not_found_exception_in_get_course_data_logs_error(
            self, send_failure_msg_to_support, log_replacement,
            get_course_data, create_course_section, create_new_course):
        """
        Test that the logger.error logs error when when get_course_data throws
        an ObjectDoesNotExist exception.
        """
        get_course_data.side_effect = ObjectDoesNotExist
        with self.assertRaises(SISCourseDoesNotExistError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
        self.assertTrue(log_replacement.error.called)

    """
     Tests for create_canvas_course.CanvasCourseGenerationJob.objects.create
    """

    @patch('canvas_course_site_wizard.models.CanvasCourseGenerationJob.objects.create')
    def test_create_canvas_course_method_invokes_create_generation_record(self, canvas_content_gen_create, get_course_data,
                                                             create_course_section, create_new_course, **kwargs):
        """
        Test that create_canvas_course method invokes a creation of CanvasCourseGenerationJob record
        with  workflow_state to STATUS_SETUP
        """
        controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
        self.assertTrue(canvas_content_gen_create.called)
        canvas_content_gen_create.assert_called_with(sis_course_id=self.sis_course_id, created_by_user_id=self.sis_user_id,
                                                      workflow_state=CanvasCourseGenerationJob.STATUS_SETUP)

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    @patch('canvas_course_site_wizard.models.CanvasCourseGenerationJob.objects.create')
    def test_create_canvas_course_method_does_not_invoke_create_generation_record_for_bulk_job(
            self, canvas_content_gen_create,
            course_generation_job__objects__filter, 
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course, **kwargs):
        """
        Test that create_canvas_course method does not try to create 
        CanvasCourseGenerationJob record for courses created by bulk job as well
        """
        query_set = Mock(get=Mock(return_value=Mock(spec=CanvasCourseGenerationJob)))
        course_generation_job__objects__filter.return_value = query_set
        controller.create_canvas_course(self.sis_course_id, self.sis_user_id,
                                        self.bulk_job_id)
        self.assertFalse(canvas_content_gen_create.called)

    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob')
    def test_create_canvas_course_method_creates_generation_record(self, canvas_content_gen_db_mock, get_course_data,
                                                             create_course_section, create_new_course, **kwargs):
        """
        Test that create_canvas_course method creates a CanvasCourseGenerationJob record with right parameters
        """
        workflow_mock = MagicMock(workflow_status=CanvasCourseGenerationJob.STATUS_SETUP)

        controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
        args, kwargs = canvas_content_gen_db_mock.objects.create.call_args
        canvas_content_gen_db_mock.objects.create.assert_called_with(sis_course_id=self.sis_course_id,
                                                                      created_by_user_id=self.sis_user_id,
                                                                      workflow_state=ANY)

    @patch('canvas_course_site_wizard.controller.logger')
    @patch('canvas_course_site_wizard.models.CanvasCourseGenerationJob.objects.create')
    def test_create_canvas_course_method_logs_on_job_creation_exception(self, canvas_content_gen_db_mock, logger, get_course_data,
                                                             create_course_section, create_new_course, **kwargs):
        """
        Test that create_canvas_course method logs an error when CanvasCourseGenerationJob creation has an exception
        """
        canvas_content_gen_db_mock.side_effect= Exception
        with self.assertRaises(Exception):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
        self.assertTrue(logger.exception.called)

    @patch('canvas_course_site_wizard.models.CanvasCourseGenerationJob.objects.create')
    def test_custome_error_raised_when_job_creation_has_exception(self, canvas_content_gen_db_mock, get_course_data,
                                                             create_course_section, create_new_course):
        """
        Test to assert that a CourseGenerationJobCreationError is raised when CanvasCourseGenerationJob creation has an exception
        """
        canvas_content_gen_db_mock.side_effect= Exception
        with self.assertRaises(CourseGenerationJobCreationError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    def test_404_exception_n_create_new_course_method_invokes_update_workflow_state(self, update_mock, get_course_data,
                                                            create_course_section, create_new_course):
        """
        A RenderableException should be raised and and
        update_content_generation_workflow_state() is invoked
        when the create_new_course SDK call throws an CanvasAPIError
        """
        create_new_course.side_effect = CanvasAPIError(status_code=404)
        with self.assertRaises(CanvasCourseCreateError):
            controller.create_canvas_course(
                self.sis_course_id,
                self.sis_user_id
            )
        update_mock.assert_called_with(
            self.sis_course_id,
            CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
            course_job_id=ANY,
            bulk_job_id=None
        )

    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    def test_404_exception_n_create_new_course_method_invokes_update_workflow_state_with_bulk_job_id(
            self, update_mock, course_generation_job__objects__filter,
            get_course_data, create_course_section, create_new_course):
        """
        Test to assert that a CanvasCourseCreateError is raised when the 
        create_new_course SDK call throws a CanvasAPIError,
        and update_content_migration_workflow_state is invoked to update the
        status to STATUS_SETUP_FAILED
        """
        query_set = Mock(get=Mock(return_value=Mock(spec=CanvasCourseGenerationJob)))
        course_generation_job__objects__filter.return_value = query_set
        create_new_course.side_effect = CanvasAPIError(status_code=404)
        with self.assertRaises(CanvasCourseCreateError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id,
                                            bulk_job_id=self.bulk_job_id)
        update_mock.assert_called_with(
            self.sis_course_id, CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
            course_job_id=None, bulk_job_id=self.bulk_job_id)

    # ------------------------------------------------------
    # Tests for create_canvas_course.create_course_section()
    # ------------------------------------------------------
    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.create')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    @patch('canvas_course_site_wizard.controller.logger')
    @patch('canvas_course_site_wizard.controller.SDK_CONTEXT')
    def test_create_new_course_method_is_called_with_proper_arguments(self,
            SDK_CONTEXT, logger, course_generation_job__objects__filter,
            course_generation_job__objects__create,
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course):
        """
        Test to assert that create_new_course method is called by 
        create_canvas_course controller method with appropriate arguments
        (collapses a bunch of individual parameter tests)
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        course_generation_job__objects__create.return_value = job
        query_set = Mock(get=Mock(return_value=job))
        course_generation_job__objects__filter.return_value = query_set
        course_model_mock = self.get_mock_of_get_course_data()
        get_course_data.return_value = course_model_mock
        sis_account_id_argument = 'sis_account_id:' + course_model_mock.sis_account_id
        course_code_argument = course_model_mock.course_code
        course_name_argument = course_model_mock.course_name
        course_term_id_argument = 'sis_term_id:' + course_model_mock.sis_term_id
        course_sis_course_id_argument = self.sis_course_id
        course_shopping_active = course_model_mock.shopping_active

        controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
        create_new_course.assert_called_with(
            request_ctx=SDK_CONTEXT,
            account_id=sis_account_id_argument,
            course_name=course_name_argument,
            course_course_code=course_code_argument,
            course_term_id=course_term_id_argument,
            course_sis_course_id=course_sis_course_id_argument,
            course_is_public_to_auth_users=course_shopping_active
        )

    def test_exception_when_create_new_course_method_raises_api_400(self, get_course_data,
                                                            create_course_section, create_new_course):
        """
        Test to assert that a CanvasCourseAlreadyExistsError is raised when the create_new_course method
        throws a CanvasAPIError
        """
        create_new_course.side_effect = CanvasAPIError(status_code=400)
        with self.assertRaises(CanvasCourseAlreadyExistsError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)

    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_exception_when_create_new_course_method_raises_api_404(self, send_failure_msg_to_support, get_course_data,
                                                            create_course_section, create_new_course):
        """
        Test to assert that a RenderableException is raised when the create_new_course SDK call
        throws an CanvasAPIError
        """
        create_new_course.side_effect = CanvasAPIError(status_code=404)
        with self.assertRaises(CanvasCourseCreateError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)

    # ------------------------------------------------------
    # Tests for create_canvas_course.create_course_section()
    # ------------------------------------------------------

    @patch('canvas_course_site_wizard.controller.SDK_CONTEXT')
    def test_create_course_section_method_is_called(self, SDK_CONTEXT, get_course_data,
                                                    create_course_section, create_new_course):
        """
        Test to assert that create_new_course method is called by create_canvas_course controller method
        """
        course_model_mock = self.get_mock_of_get_course_data()
        get_course_data.return_value = course_model_mock
        mock_canvas_course_id = '12345'
        mock_primary_section_name = course_model_mock.primary_section_name.return_value
        create_new_course.return_value.json.return_value = {'id': mock_canvas_course_id}
        controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
        create_course_section.assert_called_with(request_ctx=SDK_CONTEXT, course_id=mock_canvas_course_id,
                                                 course_section_name=mock_primary_section_name,
                                                 course_section_sis_section_id=self.sis_course_id)

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.create')
    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_when_create_course_section_method_raises_api_error(self,
            course_generation_job__objects__create,
            update_course_generation_workflow_state, send_failure_msg_to_support,
            get_course_data, create_course_section, create_new_course):
        """
        Test to assert that a RenderableException is raised when the create_course_section SDK call
        throws an CanvasAPIError
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        course_generation_job__objects__create.return_value = job
        create_course_section.side_effect = CanvasAPIError(status_code=400)
        with self.assertRaises(RenderableException):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id, None)


    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_object_not_found_exception_in_get_course_data_sends_support_email(self, send_failure_msg_to_support,
                                                                               get_course_data,
                                                           create_course_section, create_new_course):
        """
        Test to assert that a support email is sent  when get_course_data raises an ObjectDoesNotExist
        """

        get_course_data.side_effect = ObjectDoesNotExist
        exception_data = SISCourseDoesNotExistError(self.sis_course_id)

        with self.assertRaises(SISCourseDoesNotExistError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
        send_failure_msg_to_support.assert_called_with(self.sis_course_id, self.sis_user_id, exception_data.display_text)

    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.create')
    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_object_not_found_exception_in_get_course_data_doesnt_send_support_email_for_bulk_created_course(
            self, course_generation_job__objects__create, 
            send_failure_msg_to_support,
            get_course_data, create_course_section, create_new_course):
        """
        Test to assert that for a course that is created as part of a bulk job,
        the support email is not sent when get_course_data raises an
        ObjectDoesNotExist
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        course_generation_job__objects__create.return_value = job
        get_course_data.side_effect = ObjectDoesNotExist

        with self.assertRaises(CourseGenerationJobNotFoundError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id,
                                            self.bulk_job_id)
        self.assertFalse(send_failure_msg_to_support.called)

    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_canvas_course_create_error_sends_support_email(self, send_failure_msg_to_support, get_course_data,
                                                           create_course_section, create_new_course):
        """
        Test to assert that a support email is sent  when  there is an CanvasAPIError resulting in CanvasCourseCreateError
        and that the correct error message from the exception is sent as a param  to the mail helper method
        """
        create_new_course.side_effect = CanvasAPIError(status_code=404)
        exception_data = CanvasCourseCreateError(msg_details=self.sis_course_id)
        with self.assertRaises(CanvasCourseCreateError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)

        send_failure_msg_to_support.assert_called_with(self.sis_course_id, self.sis_user_id, exception_data.display_text)
        self.assertTrue('Error: SIS ID not applied for CID' in exception_data.display_text)

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_canvas_course_create_error_doesnt_send_support_email_for_bulk_created_course(
            self, send_failure_msg_to_support,
            course_generation_job__objects__filter, 
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course):
        """
        Test to assert that a for a course that is created as part of a bulk 
        job, the support email is not sent when there is an CanvasAPIError
        resulting in CanvasCourseCreateError.
        """
        query_set = Mock(get=Mock(return_value=Mock(spec=CanvasCourseGenerationJob)))
        course_generation_job__objects__filter.return_value = query_set
        create_new_course.side_effect = CanvasAPIError(status_code=404)
        with self.assertRaises(CanvasCourseCreateError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id,
                                            self.bulk_job_id)
        self.assertFalse(send_failure_msg_to_support.called)

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.create')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_canvas_section_error_sends_support_email(self,
            send_failure_msg_to_support,
            course_generation_job__objects__filter, 
            course_generation_job__objects__create, 
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course):
        """
        Test to assert that a support email is sent when there is a
        CanvasAPIError resulting in CanvasSectionCreateError.
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        course_generation_job__objects__create.return_value = job
        query_set = Mock(get=Mock(return_value=job))
        course_generation_job__objects__filter.return_value = query_set
        create_course_section.side_effect = CanvasAPIError(status_code=400)

        exception_data = CanvasSectionCreateError(self.sis_course_id)
        with self.assertRaises(CanvasSectionCreateError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)

        send_failure_msg_to_support.assert_called_with(self.sis_course_id,
                                                       self.sis_user_id,
                                                       exception_data.display_text)

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_canvas_section_error_doesnt_send_support_email_for_bulk_created_course(
            self, send_failure_msg_to_support,
            course_generation_job__objects__filter, 
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course):
        """
        Test to assert that a support email is NOT sent for bulk created courses, when  there is an CanvasAPIError
         resulting in CanvasSectionCreateError

        """
        query_set = Mock(get=Mock(return_value=Mock(spec=CanvasCourseGenerationJob)))
        course_generation_job__objects__filter.return_value = query_set
        create_course_section.side_effect = CanvasAPIError(status_code=400)

        with self.assertRaises(CanvasSectionCreateError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id,
                                            self.bulk_job_id)

        self.assertFalse(send_failure_msg_to_support.called)

    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_canvas_course_exists_error_doesnt_send_support_email(self, send_failure_msg_to_support, get_course_data,
                                                           create_course_section, create_new_course):
        """
        Test to assert that a support email is NOT sent when canvas course already exists
        (there is a CanvasCourseAlreadyExistsError)
        
        """
        create_new_course.side_effect = CanvasAPIError(status_code=400)
        with self.assertRaises(CanvasCourseAlreadyExistsError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
        
        self.assertFalse(send_failure_msg_to_support.called)


    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.create')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_canvas_section_error_sets_support_notified(self,
            send_failure_msg_to_support,
            course_generation_job__objects__filter, 
            course_generation_job__objects__create, 
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course):
        """
        Test to assert that support_notified is set on CanvasSectionCreateError
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        course_generation_job__objects__create.return_value = job
        query_set = Mock(get=Mock(return_value=job))
        course_generation_job__objects__filter.return_value = query_set
        create_course_section.side_effect = CanvasAPIError(status_code=400)
        exception_data = CanvasSectionCreateError(self.sis_course_id)
        with self.assertRaises(CanvasSectionCreateError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)

        self.assertTrue(exception_data.support_notified)

    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_canvas_course_create_error_sets_support_notified(self, send_failure_msg_to_support, get_course_data,
                                                           create_course_section, create_new_course):
        """
        Test to assert that support_notified is set on CanvasCourseCreateError
        """
        create_new_course.side_effect = CanvasAPIError(status_code=404)
        exception_data = CanvasCourseCreateError(msg_details=self.sis_course_id)
        with self.assertRaises(CanvasCourseCreateError):
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)

        self.assertTrue(exception_data.support_notified)

    @patch('canvas_course_site_wizard.controller.send_failure_msg_to_support')
    def test_canvas_course_already_exists_error_doesnt_set_support_notified(self, send_failure_msg_to_support, get_course_data,
                                                           create_course_section, create_new_course):
        """
        Test to assert that support_notified is NOT set on CanvasCourseAlreadyExistsError
        """
        create_new_course.side_effect = CanvasAPIError(status_code=400)
        with self.assertRaises(CanvasCourseAlreadyExistsError) as cm:
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)

        self.assertTrue('support_notified' not in cm.exception)

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.create')
    def test_canvas_course_id_saved_to_canvas_course_generation_job_single(self,
            course_generation_job__objects__create, 
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course):
        """
        Ensures that the canvas course id is saved to the
        CanvasCourseGenerationJob
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        course_generation_job__objects__create.return_value = job

        # don't edit the class-wide create_new_course mock
        with patch('canvas_course_site_wizard.controller.create_new_course') as create_new_course:
            create_new_course().json.return_value = {'id': self.canvas_course_id}
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
            self.assertEqual(job.canvas_course_id, self.canvas_course_id)
            job.save.assert_called_with(update_fields=['canvas_course_id'])

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    def test_canvas_course_id_saved_to_canvas_course_generation_job_bulk(self,
            course_generation_job__objects__filter, 
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course):
        """
        Ensures that the canvas course id is saved to the
        CanvasCourseGenerationJob
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        query_set = Mock(get=Mock(return_value=job))
        course_generation_job__objects__filter.return_value = query_set

        # don't edit the class-wide create_new_course mock
        with patch('canvas_course_site_wizard.controller.create_new_course') as create_new_course:
            create_new_course().json.return_value = {'id': self.canvas_course_id}
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id,
                                            self.bulk_job_id)
            self.assertEqual(job.canvas_course_id, self.canvas_course_id)
            job.save.assert_called_with(update_fields=['canvas_course_id'])

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.create')
    def test_canvas_course_id_saved_to_course_instance_single(self,
            course_generation_job__objects__create, 
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course):
        """
        Ensures that the canvas course id is saved to the CourseInstance
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        course_generation_job__objects__create.return_value = job

        # don't edit the class-wide create_new_course mocks
        with contextlib.nested(
                patch('canvas_course_site_wizard.controller.get_course_data'),
                patch('canvas_course_site_wizard.controller.create_new_course')
                ) as (get_course_data, create_new_course):
            course_data = MagicMock(spec=SISCourseData())
            get_course_data.return_value = course_data
            create_new_course().json.return_value = {'id': self.canvas_course_id}
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id)
            self.assertEqual(course_data.canvas_course_id, self.canvas_course_id)
            course_data.save.assert_called_with(update_fields=['canvas_course_id'])

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    @patch('canvas_course_site_wizard.controller.CanvasCourseGenerationJob.objects.filter')
    def test_canvas_course_id_saved_to_course_instance_bulk(self,
            course_generation_job__objects__filter, 
            update_course_generation_workflow_state, get_course_data,
            create_course_section, create_new_course):
        """
        Ensures that the canvas course id is saved to the CourseInstance
        """
        job = Mock(spec=CanvasCourseGenerationJob())
        query_set = Mock(get=Mock(return_value=job))
        course_generation_job__objects__filter.return_value = query_set

        # don't edit the class-wide create_new_course mocks
        with contextlib.nested(
                patch('canvas_course_site_wizard.controller.get_course_data'),
                patch('canvas_course_site_wizard.controller.create_new_course')
                ) as (get_course_data, create_new_course):
            course_data = MagicMock(spec=SISCourseData())
            get_course_data.return_value = course_data
            create_new_course().json.return_value = {'id': self.canvas_course_id}
            controller.create_canvas_course(self.sis_course_id, self.sis_user_id,
                                            self.bulk_job_id)
            self.assertEqual(course_data.canvas_course_id, self.canvas_course_id)
            course_data.save.assert_called_with(update_fields=['canvas_course_id'])
