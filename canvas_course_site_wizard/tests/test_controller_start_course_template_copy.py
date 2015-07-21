from canvas_course_site_wizard.controller import start_course_template_copy
from canvas_course_site_wizard.models import SISCourseData, CanvasCourseGenerationJob, CanvasSchoolTemplate
from canvas_course_site_wizard.exceptions import NoTemplateExistsForSchool
from unittest import TestCase
from mock import patch, DEFAULT, Mock, MagicMock, ANY
from django.core.exceptions import ObjectDoesNotExist

import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

m_canvas_content_migration_job = Mock(
    spec=CanvasCourseGenerationJob,
    id=2,
    canvas_course_id=9999,
    sis_course_id=88323,
    status_url='http://example.com/1234',
    workflow_state='setup',
    created_by_user_id='123'
)

# m_workflow_status
 
@patch.multiple('canvas_course_site_wizard.controller', get_default_template_for_school=DEFAULT, content_migrations=DEFAULT,
                CanvasCourseGenerationJob=DEFAULT, SDK_CONTEXT=DEFAULT, get_course_generation_data_for_sis_course_id=DEFAULT)
class StartCourseTemplateCopyTest(TestCase):
    longMessage = True

    def setUp(self):
        self.template = Mock(
            spec=CanvasSchoolTemplate,
            id=54321,
            school_id='colgsas',
            template_id=54321,
            is_default=True
        )
        self.canvas_course_id = 9999
        self.user_id = 123
        self.sis_course_data = Mock(
            pk=88323,
            spec=SISCourseData,
            school_code='fas',
        )
        self.content_migration_json = {
            'id': '52322',
            'progress_url': 'http://canvas.instructure.com/api/v1/progress/5',
        }

    def test_get_default_template_for_school_called_with_school_code(self, get_default_template_for_school, **kwargs):
        """
        Test that controller method calls get_default_template_for_school with expected parameter
        """
        # iterable_ccmjob_mock = MagicMock()
        # filter_mock.return_value = iterable_ccmjob_mock
        # iterable_ccmjob_mock.__iter__ = Mock(return_value=iter([self.m_canvas_content_migration_job]))


        start_course_template_copy(self.sis_course_data, self.canvas_course_id, self.user_id)
        get_default_template_for_school.assert_called_with(self.sis_course_data.school_code)

    def test_custom_exception_raised_if_no_template_for_school(self, get_default_template_for_school, **kwargs):
        """
        Test that if an NoTemplateExistsForSchool exception gets triggered when retrieving the school
        template, a NoTemplateExistsForCourse exception is raised back to the caller.
        """
        get_default_template_for_school.side_effect = NoTemplateExistsForSchool("")
        with self.assertRaises(NoTemplateExistsForSchool):
            start_course_template_copy(self.sis_course_data, self.canvas_course_id, self.user_id)

    def test_content_migration_copy_called_with_context_positional_arg(self, content_migrations, SDK_CONTEXT, **kwargs):
        """
        Test that SDK call to initiate course copy has SDK_CONTEXT as a positional argument
        """
        start_course_template_copy(self.sis_course_data, self.canvas_course_id, self.user_id)
        args, kwargs = content_migrations.create_content_migration_courses.call_args
        self.assertTrue(SDK_CONTEXT in args)

    def test_content_migration_copy_called_with_canvas_course_id_positional_arg(self, content_migrations, **kwargs):
        """
        Test that SDK call to initiate course copy has the canvas_course_id as a positional argument
        """
        start_course_template_copy(self.sis_course_data, self.canvas_course_id, self.user_id)
        args, kwargs = content_migrations.create_content_migration_courses.call_args
        self.assertTrue(self.canvas_course_id in args)

    def test_content_migration_copy_called_with_expected_migration_type_keyword(self, content_migrations, **kwargs):
        """
        Test that SDK call to initiate course copy has the right migration_type specified
        """
        expected_migration_type = 'course_copy_importer'
        start_course_template_copy(self.sis_course_data, self.canvas_course_id, self.user_id)
        args, kwargs = content_migrations.create_content_migration_courses.call_args
        self.assertEqual(kwargs.get('migration_type'), expected_migration_type)

    def test_content_migration_copy_called_with_expected_templated_id_keyword(self, content_migrations,
                                                                              get_default_template_for_school, **kwargs):
        """
        Test that SDK call to initiate course copy has the expected template id specified
        """
        get_default_template_for_school.return_value = self.template
        start_course_template_copy(self.sis_course_data, self.canvas_course_id, self.user_id)
        args, kwargs = content_migrations.create_content_migration_courses.call_args
        self.assertEqual(kwargs.get('settings_source_course_id'), self.template.template_id)

    def test_content_migration_job_row_updated(self,content_migrations, get_course_generation_data_for_sis_course_id,
                                                **kwargs):
        """
        Test that start_course_template_copy results in the content migration job row getting saved with the right params
        """

        get_course_generation_data_for_sis_course_id.return_value = m_canvas_content_migration_job
        ret = start_course_template_copy(self.sis_course_data, self.canvas_course_id, self.user_id)
        m_canvas_content_migration_job.save.assert_called_with(update_fields=['canvas_course_id', 'content_migration_id',
                                                                                'status_url', 'workflow_state',
                                                                              'created_by_user_id'])
        # self.assertEqual(ret.workflow_state,  mock_queued)

    @patch('canvas_course_site_wizard.controller.update_course_generation_workflow_state')
    def test_exception_results_in_worflow_state_getting_updated (self, update_mock, get_default_template_for_school, **kwargs):
        """
        Test that if an NoTemplateExistsForSchool exception gets triggered when retrieving the school
        template,  the update_content_migration_workflow_state is called to set the state to STATUS_SETUP_FAILED
        """
        get_default_template_for_school.side_effect = NoTemplateExistsForSchool("")
        with self.assertRaises(NoTemplateExistsForSchool):
            start_course_template_copy(self.sis_course_data, self.canvas_course_id, self.user_id)
            update_mock.assert_called_with(self.sis_course_data, CanvasCourseGenerationJob.STATUS_SETUP_FAILED)
