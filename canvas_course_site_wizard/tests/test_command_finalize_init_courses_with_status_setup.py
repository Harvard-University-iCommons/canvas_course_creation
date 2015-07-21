from django.test import TestCase
from mock import patch, ANY, DEFAULT, Mock, MagicMock, call
from canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs import _init_courses_with_status_setup
from canvas_course_site_wizard.models import CanvasCourseGenerationJob, BulkCanvasCourseCreationJob
from canvas_course_site_wizard.management.commands import finalize_bulk_create_jobs
from canvas_course_site_wizard.exceptions import (NoTemplateExistsForSchool,
                                                  CanvasCourseAlreadyExistsError,
                                                  CourseGenerationJobCreationError)
def start_job_with_noargs():
    cmd = finalize_bulk_create_jobs.Command()
    cmd.handle_noargs()

class ContentMigrationJob:

    def __init__(self, pk, bulk_job_id, created_by_user_id, sis_course_id, state):
        self.pk = pk
        self.bulk_job_id = bulk_job_id
        self.created_by_user_id = created_by_user_id
        self.sis_course_id = sis_course_id
        self.workflow_state = state

    def update_workflow_state(self, state):
        self.workflow_state = state


@patch.multiple('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs',
                get_course_data=DEFAULT, create_canvas_course=DEFAULT, start_course_template_copy=DEFAULT)
class FinalizeInitCoursesWithStatusSetupCommandTests(TestCase):

    def setUp(self):
        self.user_id = '12345678'
        self.bulk_job_id = 12345
        self.template_id = 54321
        self.school_code = 'colgsas'
        self.sis_term_id = 4579
        self.courses = [123, 456, 789, 1011, 1012, 1013, 1014, 1015]
        self.cm_jobs = []
        for idx, course in enumerate(self.courses):
            migration_job = ContentMigrationJob(
                idx,
                self.bulk_job_id,
                self.user_id,
                course,
                CanvasCourseGenerationJob.STATUS_SETUP
            )
            self.cm_jobs.append(migration_job)
        self.bulk_jobs = [BulkCanvasCourseCreationJob(
            id=self.bulk_job_id,
            school_id=self.school_code,
            template_canvas_course_id=self.template_id,
            status=BulkCanvasCourseCreationJob.STATUS_SETUP,
            created_by_user_id=self.user_id
        )]

    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.BulkJob.objects.filter')
    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.'
           'CanvasCourseGenerationJob.objects.filter_setup_for_bulkjobs')
    def test_that_create_course_is_call_with_all_bulk_job_courses(self, mock_getjobs, mock_filter_bulk_jobs,
                                                                  get_course_data, create_canvas_course,
                                                                  start_course_template_copy):
        """
        test that create_canvas_course is called with all the courses that have a status of 'setup'
        """
        mock_getjobs.return_value = self.cm_jobs
        mock_filter_bulk_jobs.return_value = self.bulk_jobs
        create_course_calls = []
        template_copy_calls = []
        for index, course in enumerate(self.courses):
            create_course_calls.append(call(course, self.user_id, bulk_job_id=self.bulk_job_id))
            create_course_calls.append(ANY)
            template_copy_calls.append(
                call(ANY, ANY, self.user_id, course_job_id=index,
                     bulk_job_id=self.bulk_job_id, template_id=self.template_id)
            )

        _init_courses_with_status_setup()
        create_canvas_course.assert_has_calls(create_course_calls)
        start_course_template_copy.assert_has_calls(template_copy_calls)

    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.BulkJob.objects.filter')
    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.logger.exception')
    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.'
           'CanvasCourseGenerationJob.objects.filter_setup_for_bulkjobs')
    def test_that_logger_is_called_when_course_already_exists(self, mock_getjobs, mock_logger, mock_filter_bulk_jobs,
                                                              get_course_data, create_canvas_course,
                                                              start_course_template_copy):
        """
        test that logger is called when the course already exists in canvas
        """
        mock_getjobs.return_value = self.cm_jobs
        mock_filter_bulk_jobs.return_value = self.bulk_jobs
        create_logger_calls = []
        for course in self.courses:
            create_logger_calls.append(call('content migration error for course with id %s' % course))

        create_canvas_course.side_effect = CanvasCourseAlreadyExistsError(msg_details=123)
        _init_courses_with_status_setup()
        mock_logger.assert_has_calls(create_logger_calls)

    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.BulkJob.objects.filter')
    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.logger.exception')
    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.'
           'CanvasCourseGenerationJob.objects.filter_setup_for_bulkjobs')
    def test_that_logger_is_called_when_course_generation_fails(self, mock_getjobs, mock_logger, mock_filter_bulk_jobs,
                                                                get_course_data, create_canvas_course,
                                                                start_course_template_copy):
        """
        test that logger is called when the course generation fails
        """
        mock_getjobs.return_value = self.cm_jobs
        mock_filter_bulk_jobs.return_value = self.bulk_jobs
        content_migration_error_calls = []
        for course in self.courses:
            content_migration_error_calls.append(call('content migration error for course with id %s' % course))

        create_canvas_course.side_effect = CourseGenerationJobCreationError(msg_details=123)
        _init_courses_with_status_setup()
        mock_logger.assert_has_calls(content_migration_error_calls)


    @patch('canvas_course_site_wizard.models.'
           'CanvasCourseGenerationJob.update_workflow_state')
    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.logger.exception')

    @patch('canvas_course_site_wizard.management.commands.finalize_bulk_create_jobs.'
           'CanvasCourseGenerationJob.objects.filter_setup_for_bulkjobs')
    def test_that_workflow_state_is_properly_updated_when_no_template_exists(self, mock_getjobs, mock_job_update, mock_logger, get_course_data, create_canvas_course, start_course_template_copy):
        """
        test that logger is called when there is no course template
        """
        mock_getjobs.return_value = self.cm_jobs
        template_calls = []
        finalize_calls = []
        for course in self.courses:
            template_calls.append(call('no template for course instance id %s' % course))
        start_course_template_copy.side_effect = NoTemplateExistsForSchool(self.school_code)
        _init_courses_with_status_setup()
        # make sure that the job's status is updated to STATUS_PENDING_FINALIZE
        mock_job_update.assertCalledWith(CanvasCourseGenerationJob.STATUS_PENDING_FINALIZE)

