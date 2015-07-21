from unittest import TestCase
from mock import patch, DEFAULT
from icommons_ui.exceptions import RenderableException
from django.core.exceptions import ObjectDoesNotExist
from canvas_course_site_wizard.models import SISCourseData
from canvas_course_site_wizard.controller import finalize_new_canvas_course


@patch.multiple('canvas_course_site_wizard.controller', enroll_creator_in_new_course=DEFAULT, logger=DEFAULT,
                get_course_data=DEFAULT, get_canvas_course_url=DEFAULT)
class FinalizeNewCanvasCourseTest(TestCase):
    def setUp(self):
        self.canvas_course_id = '123'
        self.sis_course_id = '123456'
        self.user_id = 999
        self.test_return_value = None
        self.bulk_job_id = 10

    def test_finalization_success(self, enroll_creator_in_new_course, logger, get_course_data, get_canvas_course_url):
        """
        If all finalization steps are successful, there should be no calls to logger.exception() and the return value
        should be the new course URL.
        """
        test_url = 'test_url/'
        get_canvas_course_url.return_value = test_url
        self.test_return_value = finalize_new_canvas_course(self.canvas_course_id, self.sis_course_id, self.user_id)
        self.assertFalse(logger.exception.called)
        self.assertEquals(self.test_return_value, test_url)

    # Enroll instructor / creator

    def test_enrollment_failure(self, enroll_creator_in_new_course, logger, get_course_data, get_canvas_course_url):
        """
        If the automatic enrollment of the course creator fails, we should be logging an exception and exiting the
        finalization process without a return value and before proceeding with other steps.
        """
        enroll_creator_in_new_course.side_effect = Exception('Mock exception')
        with self.assertRaises(RenderableException):
            self.test_return_value = finalize_new_canvas_course(self.canvas_course_id, self.sis_course_id, self.user_id)
        enroll_creator_in_new_course.assert_called_once_with(self.sis_course_id, self.user_id)
        self.assertFalse(get_course_data.called)
        self.assertTrue(logger.exception.called)
        self.assertIsNone(self.test_return_value)

    # Copy SIS enrollments to new Canvas course

    def test_course_data_failure(self, enroll_creator_in_new_course, logger, get_course_data, get_canvas_course_url):
        """
        If unable to get SIS course data for the course (which we need to mark the Canvas course as official and
        sync enrollment to Canvas), we should be logging an exception and exiting the
        finalization process without a return value and before proceeding with other steps.
        """
        get_course_data.side_effect = ObjectDoesNotExist('Mock exception')
        with self.assertRaises(RenderableException):
            self.test_return_value = finalize_new_canvas_course(self.canvas_course_id, self.sis_course_id, self.user_id, None)
        enroll_creator_in_new_course.assert_called_once_with(self.sis_course_id, self.user_id)
        get_course_data.assert_called_once_with(self.sis_course_id)
        self.assertTrue(logger.exception.called)
        self.assertIsNone(self.test_return_value)

    def test_sync_failure(self, enroll_creator_in_new_course, logger, get_course_data, get_canvas_course_url):
        """
        If unable to set the sync enrollment to Canvas flag for the course we should be logging an exception and exiting
        the finalization process without a return value and before proceeding with other steps.
        """
        get_course_data().set_sync_to_canvas.side_effect = Exception('Mock exception')
        with self.assertRaises(RenderableException):
            self.test_return_value = finalize_new_canvas_course(self.canvas_course_id, self.sis_course_id, self.user_id, None)
        get_course_data().set_sync_to_canvas.assert_called_with(SISCourseData.TURN_ON_SYNC_TO_CANVAS)
        self.assertFalse(get_canvas_course_url.called)
        self.assertTrue(logger.exception.called)
        self.assertIsNone(self.test_return_value)

    # Mark course as official

    def test_course_url_failure(self, enroll_creator_in_new_course, logger, get_course_data, get_canvas_course_url):
        """
        If unable to get a Canvas course URL for the new course, we should be logging an exception and exiting the
        finalization process without a return value and before proceeding with other steps.
        """
        get_canvas_course_url.side_effect = Exception('Mock exception')
        with self.assertRaises(RenderableException):
            self.test_return_value = finalize_new_canvas_course(self.canvas_course_id, self.sis_course_id, self.user_id, None)
        get_canvas_course_url.assert_called_once_with(canvas_course_id=self.canvas_course_id)
        self.assertFalse(get_course_data().set_sync_to_canvas().called)
        self.assertTrue(logger.exception.called)
        self.assertIsNone(self.test_return_value)

    def test_set_official_failure(self, enroll_creator_in_new_course, logger, get_course_data, get_canvas_course_url):
        """
        If unable to set the Canvas course as 'official', we should be logging an exception and exiting the
        finalization process without a return value and before proceeding with other steps.
        """
        get_course_data().set_sync_to_canvas().set_official_course_site_url.side_effect = Exception('Mock exception')
        test_url = 'test_url/'
        get_canvas_course_url.return_value = test_url
        with self.assertRaises(RenderableException):
            self.test_return_value = finalize_new_canvas_course(self.canvas_course_id, self.sis_course_id, self.user_id, None)
        get_canvas_course_url.assert_called_once_with(canvas_course_id=self.canvas_course_id)
        get_course_data().set_sync_to_canvas().set_official_course_site_url.assert_called_once_with(test_url)
        self.assertTrue(logger.exception.called)
        self.assertIsNone(self.test_return_value)

    def test_creator_not_enrolled_for_bulk_created_course(self, enroll_creator_in_new_course, logger, get_course_data,
                                                          get_canvas_course_url):
        """
        Test that the the creator/initiator does not get enrolled in a course when the course is part of bulk job
        """
        test_url = 'test_url/'
        get_canvas_course_url.return_value = test_url
        self.test_return_value = finalize_new_canvas_course(self.canvas_course_id, self.sis_course_id, self.user_id,
                                                            self.bulk_job_id)
        self.assertFalse(enroll_creator_in_new_course.called)
