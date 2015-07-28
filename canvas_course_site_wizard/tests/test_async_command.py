from django.test import TestCase
from mock import patch, ANY, DEFAULT, Mock, MagicMock
from canvas_course_site_wizard.models import CanvasCourseGenerationJob
from canvas_course_site_wizard.management.commands import process_async_jobs
from canvas_course_site_wizard.exceptions import (CanvasCourseAlreadyExistsError, CopySISEnrollmentsError,
                                                  MarkOfficialError)
from django.test.utils import override_settings


def start_job_with_noargs():
    cmd = process_async_jobs.Command()
    cmd.handle_noargs()


def mock_client_json(client_mock, return_value='completed'):
    client_mock.get.return_value.json.return_value = {
        'workflow_state': return_value,
    }


def mock_user_profile(profile_mock, return_value='a@a.com'):
    profile_mock.return_value = {
        'primary_email': return_value,
    }


@override_settings(CANVAS_EMAIL_NOTIFICATION={'course_migration_success_subject': 'xyz',
                                              'course_migration_success_body': 'abc'})
@patch.multiple(
    'canvas_course_site_wizard.management.commands.process_async_jobs',
    send_failure_email=DEFAULT,
    logger=DEFAULT,
    update_syllabus_body=DEFAULT,
    finalize_new_canvas_course=DEFAULT,
    send_email_helper=DEFAULT,
    get_canvas_user_profile=DEFAULT,
    client=DEFAULT,
    tech_logger=DEFAULT
)
class CommandsTestCase(TestCase):
    """
    tests for the process_async_jobs management command.
    """
    def setUp(self):
        self.canvas_course_id = 12345
        self.sis_course_id = 6789
        self.content_migration_id = 123
        self.status_url = 'http://example.com/1234'
        self.created_by_user_id = '123'
        self.workflow_state = 'queued'
        self.status_check = {
            'workflow_state': 'completed',
        }
        self.migration = self.create_migration_job_from_setup()

    def create_migration_job_from_setup(self):
        """ Create and return a new CanvasCourseGenerationJob using values in setUp and return """
        return CanvasCourseGenerationJob.objects.create(
            canvas_course_id=self.canvas_course_id,
            sis_course_id=self.sis_course_id,
            content_migration_id=self.content_migration_id,
            status_url=self.status_url,
            created_by_user_id=self.created_by_user_id,
            workflow_state=self.workflow_state
        )

    m_canvas_content_migration_job_with_bulk_id = Mock(
        spec=CanvasCourseGenerationJob,
        id=2,
        bulk_job_id=2,
        canvas_course_id=12345,
        sis_course_id=6789,
        status_url='http://example.com/1234',
        created_by_user_id='123'
    )

    @patch('canvas_course_site_wizard.management.commands.process_async_jobs.CanvasCourseGenerationJob.objects.filter')
    def test_process_async_jobs_cm_filter_called_with(self, filter_mock, **kwargs):
        """
        test process_async_jobs called CanvasCourseGenerationJob.objects.filter with one argument
        """
        start_job_with_noargs()
        filter_mock.assert_called_once_with(ANY)

    def test_process_async_jobs_cm_assert_that_client_get_is_called_once_with_the_correct_url(self, client, **kwargs):
        """
        ** Integration test **
        assert that client.get is called with the job.status_url. Note that this
        will most likely change as the method of getting the job_id can be streamlined. At the moment
        we store the progress url in the jobs table, but we only really need to store the job_id. If that
        change happens this test will need to be replaced.
        """

        start_job_with_noargs()
        client.get.assert_called_with(ANY, self.status_url)

    def test_process_async_jobs_invokes_correct_methods_on_completed_status(self, client, get_canvas_user_profile,
            send_email_helper, **kwargs):
        """
        test that the send_email_helper and get_canvas_user_profile helper method are called
        with the right params when the workflow_state of the job changes to 'completed'
        """

        mock_client_json(client, 'completed')
        mock_user_profile(get_canvas_user_profile)

        start_job_with_noargs()
        get_canvas_user_profile.assert_called_with(self.created_by_user_id)
        send_email_helper.assert_called_once_with(ANY, ANY, ANY)

    @patch('canvas_course_site_wizard.management.commands.process_async_jobs.CanvasCourseGenerationJob.objects.filter')
    def test_process_async_jobs_doesnt_send_email_for_bulk_created_course(self, filter_mock, client,
                                                                          send_email_helper, **kwargs):
        """
        test that the send_email_helper is not called for a bulk created course,
        irrespective of the workflow_state
        """
        mock_client_json(client, 'this can be anything')
        iterable_ccmjob_mock = MagicMock()
        filter_mock.return_value = iterable_ccmjob_mock
        iterable_ccmjob_mock.__iter__ = Mock(return_value=iter([self.m_canvas_content_migration_job_with_bulk_id]))

        start_job_with_noargs()
        self.assertFalse(send_email_helper.called)

    @patch('canvas_course_site_wizard.management.commands.process_async_jobs.logger.info')
    @patch('canvas_course_site_wizard.management.commands.process_async_jobs.CanvasCourseGenerationJob.objects.filter')
    def test_process_async_jobs_on_failure_for_bulk_course_calls_tech_logger(self, mock_logger, filter_mock, client,
                                                                             get_canvas_user_profile, send_email_helper,
                                                                             tech_logger, **kwargs):
        """
        test that the tech_logger is called even for bulk jobs when there is a failure.
        """
        mock_client_json(client, 'failed')
        iterable_ccmjob_mock = MagicMock()
        filter_mock.return_value = iterable_ccmjob_mock
        iterable_ccmjob_mock.__iter__ = Mock(return_value=iter([self.m_canvas_content_migration_job_with_bulk_id]))

        start_job_with_noargs()
        self.assertTrue(mock_logger.called)

    def test_process_async_jobs_on_failed_status(self, client, get_canvas_user_profile, send_failure_email, tech_logger,
            **kwargs):
        """
        test that the send_failure_email, get_canvas_user_profile helper method, and
        tech_logger are all called when the workflow_state of the job changes to 'failed' for a non-bulk course create
        """

        mock_client_json(client, 'failed')
        mock_user_profile(get_canvas_user_profile)

        start_job_with_noargs()
        get_canvas_user_profile.assert_called_with(self.created_by_user_id)
        send_failure_email.assert_called_with(ANY, ANY)
        self.assertEqual(tech_logger.error.call_count, 1)

    def test_process_async_jobs_sends_failure_email_when_error_in_finalize_method(self, client,
            get_canvas_user_profile, finalize_new_canvas_course, send_failure_email, **kwargs):
        """
        test that the sync jobs send a failure email notification on any exception raised by finalize_new_canvas_course
        for a non-bulk created course
        """

        mock_client_json(client, 'completed')
        mock_user_profile(get_canvas_user_profile)

        finalize_new_canvas_course.side_effect = Exception
        start_job_with_noargs()
        send_failure_email.assert_called_with(ANY, ANY)

    def test_tech_logger_on_error(self, client, get_canvas_user_profile, finalize_new_canvas_course,
            send_failure_email, tech_logger, **kwargs):
        """ test that tech_logger is called on general error in process (e.g. in finalize method) """

        mock_client_json(client, 'completed')
        mock_user_profile(get_canvas_user_profile)

        finalize_new_canvas_course.side_effect = Exception
        start_job_with_noargs()
        self.assertEqual(tech_logger.exception.call_count, 1)

    def test_tech_logger_on_renderableexception(self, client, get_canvas_user_profile, finalize_new_canvas_course,
            send_failure_email, tech_logger, **kwargs):
        """ test that tech_logger uses the display_text of a RenderableException when available """

        mock_client_json(client, 'completed')
        mock_user_profile(get_canvas_user_profile)

        e = CanvasCourseAlreadyExistsError(self.sis_course_id)
        finalize_new_canvas_course.side_effect = e
        start_job_with_noargs()
        tech_logger.exception.assert_called_with('%s (HUID:%s)' % (e.display_text, self.created_by_user_id))

    def test_process_async_jobs_sends_failure_email_when_any_exception_occurs(self, client, get_canvas_user_profile,
            send_email_helper, finalize_new_canvas_course, logger, send_failure_email, **kwargs):
        """ test that the sync jobs send a failure email notification on an exception during job processing """

        client.get.side_effect = Exception
        mock_user_profile(get_canvas_user_profile)

        start_job_with_noargs()
        send_failure_email.assert_called_with(ANY, ANY)

    def test_process_async_jobs_logs_exception_thrown_by_send_email_helper(self, client, get_canvas_user_profile,
            send_email_helper, finalize_new_canvas_course, logger, **kwargs):
        """ Test that an exception is raised when send_email_helper method throws an exception """

        mock_client_json(client, 'completed')
        mock_user_profile(get_canvas_user_profile)
        send_email_helper.side_effect = Exception

        start_job_with_noargs()
        self.assertTrue(logger.exception.called)

    def test_tech_logger_on_exception_thrown_by_send_email_helper(self, client, get_canvas_user_profile,
              send_email_helper, finalize_new_canvas_course, logger, tech_logger, **kwargs):
        """ Test that tech_logger is called when send_email_helper method throws an exception """

        mock_client_json(client, 'completed')
        mock_user_profile(get_canvas_user_profile)
        send_email_helper.side_effect = Exception

        start_job_with_noargs()
        self.assertEqual(tech_logger.exception.call_count, 1)

    def test_process_async_jobs_logs_exception(self, client, get_canvas_user_profile, logger, **kwargs):
        """ Test that an exception is properly logged by the async job """
        mock_client_json(client, 'completed')
        get_canvas_user_profile.side_effect = Exception

        start_job_with_noargs()
        self.assertTrue(logger.exception.called)

    def test_no_user_profile_when_handling_exception(self, client, get_canvas_user_profile, finalize_new_canvas_course,
            logger, **kwargs):
        """ When handling an exception, if there is not yet a canvas user profile then we should attempt to fetch it """
        mock_client_json(client, 'completed')
        finalize_new_canvas_course.side_effect = Exception

        start_job_with_noargs()
        self.assertEqual(get_canvas_user_profile.call_count, 1)

    def test_job_workflow_state_saved_when_status_complete_and_finalize_throws_exception(self, client,
            get_canvas_user_profile, send_email_helper, finalize_new_canvas_course, **kwargs):
        """
        Test that the  CanvasCourseGenerationJob's  workflow state is updated to STATUS_FINALIZE_FAILED
        when there is an exception in finalizing
        """
        mock_client_json(client, CanvasCourseGenerationJob.STATUS_COMPLETED)
        finalize_new_canvas_course.side_effect = Exception

        start_job_with_noargs()
        cm = CanvasCourseGenerationJob.objects.get(pk=self.migration.pk)
        self.assertEqual(cm.workflow_state, CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED)

    def test_job_workflow_state_saved_when_status_failed_and_finalize_throws_exception(self, client,
            get_canvas_user_profile, send_email_helper, finalize_new_canvas_course, **kwargs):
        """
        Test that the CanvasCourseGenerationJob's  workflow state is updated to failure
        regardless of whether finalizing throws an exception
        """
        mock_client_json(client, 'failed')
        finalize_new_canvas_course.side_effect = Exception

        start_job_with_noargs()
        cm = CanvasCourseGenerationJob.objects.get(pk=self.migration.pk)
        self.assertEqual(cm.workflow_state, CanvasCourseGenerationJob.STATUS_FAILED)

    def test_job_workflow_state_saved_after_finalize_success(self, client,
            get_canvas_user_profile, send_email_helper, finalize_new_canvas_course, **kwargs):
        """
        Test that the  CanvasCourseGenerationJob's  state is updated from 'complete' to
         CanvasCourseGenerationJob.STATUS_FINALIZED after finalize is  successful
        """
        mock_client_json(client, CanvasCourseGenerationJob.STATUS_COMPLETED)

        start_job_with_noargs()
        cm = CanvasCourseGenerationJob.objects.get(pk=self.migration.pk)
        self.assertEqual(cm.workflow_state, CanvasCourseGenerationJob.STATUS_FINALIZED)


    def test_job_workflow_state_saved_when_finalize_fails_during_sync_to_canvas(self, client,
            get_canvas_user_profile, send_email_helper, finalize_new_canvas_course, **kwargs):
        """
        Test that the  CanvasCourseGenerationJob's workflow state is updated from
        CanvasCourseGenerationJob.STATUS_COMPLETED to CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED
        when finalize fails due to CopySISEnrollmentsError Exception(set_sync_to_canvas fails)
        """
        mock_client_json(client, CanvasCourseGenerationJob.STATUS_COMPLETED)
        finalize_new_canvas_course.side_effect = CopySISEnrollmentsError
        start_job_with_noargs()
        cm = CanvasCourseGenerationJob.objects.get(pk=self.migration.pk)
        self.assertEqual(cm.workflow_state, CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED)

    def test_job_workflow_state_saved_when_finalize_fails_due_to_mark_official(self, client,
            get_canvas_user_profile, send_email_helper, finalize_new_canvas_course, **kwargs):
        """
        Test that the  CanvasCourseGenerationJob's workflow state is updated from CanvasCourseGenerationJob.STATUS_COMPLETED to
         CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED when finalize fails due to
         MarkOfficialError Exception (mark official failure)
        """
        mock_client_json(client, CanvasCourseGenerationJob.STATUS_COMPLETED)
        finalize_new_canvas_course.side_effect = MarkOfficialError
        start_job_with_noargs()
        cm = CanvasCourseGenerationJob.objects.get(pk=self.migration.pk)
        self.assertEqual(cm.workflow_state, CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED)

