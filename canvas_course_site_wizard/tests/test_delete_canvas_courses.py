from canvas_sdk.exceptions import CanvasAPIError
from django.test import TestCase
from django.core.management import call_command
from mock import patch, DEFAULT, MagicMock

from canvas_course_site_wizard.management.commands.delete_canvas_courses import (
    process_course,
    validate_course,
    get_list_sections,
    process_sections,
    delete_enrollments_for_section,
    unmark_course_as_official, unsync_from_canvas_and_reset_canvas_id)


@patch.multiple('canvas_course_site_wizard.management.commands.delete_canvas_courses',
                get_canvas_course_lookup_id=DEFAULT,
                process_course=DEFAULT)
class DeleteScriptCommandTestCase(TestCase):
    """ tests for the delete_canvas_courses management command. """

    def test_no_args(self, get_canvas_course_lookup_id, process_course, **kwargs):
        """ If no arguments are provided to the command then no courses should be affected """
        call_command('delete_canvas_courses')
        self.assertFalse(get_canvas_course_lookup_id.called)
        self.assertFalse(process_course.called)

    def test_sis_courses(self, get_canvas_course_lookup_id, process_course, **kwargs):
        """ If the course list uses Course Instance IDs then check that it's in our db before continuing """
        call_command('delete_canvas_courses', '1', '2', course_instance_ids=True)
        self.assertEqual(get_canvas_course_lookup_id.call_count, 2)
        self.assertEqual(process_course.call_count, 2)

    def test_default_options(self, get_canvas_course_lookup_id, process_course, **kwargs):
        """ If course list uses Canvas IDs, do not check the if the course is in our db before processing """
        call_command('delete_canvas_courses', '1', '2')
        self.assertFalse(get_canvas_course_lookup_id.called)
        self.assertEqual(process_course.call_count, 2)


@patch.multiple('canvas_course_site_wizard.management.commands.delete_canvas_courses',
                validate_course=DEFAULT,
                get_list_sections=DEFAULT,
                process_sections=DEFAULT,
                delete_course=DEFAULT,
                unsync_from_canvas_and_reset_canvas_id=DEFAULT,
                unmark_course_as_official=DEFAULT)
class DeleteScriptProcessCourseHelperTestCase(TestCase):

    def test_process_course_no_course_id(self, validate_course, **kwargs):
        """ if no course id provided, no need to continue """
        process_course(None)
        self.assertFalse(validate_course.called)

    def test_process_course_found_no_course(self, validate_course, get_list_sections, **kwargs):
        """ if no course found in our DB, no need to continue """
        validate_course.return_value = None
        process_course('1')
        self.assertFalse(get_list_sections.called)

    def test_process_course_uses_correct_id(self, validate_course, get_list_sections, process_sections, delete_course, unsync_from_canvas_and_reset_canvas_id, unmark_course_as_official):
        """
        if lookup id uses sis_course_id, the deletion steps
        should still use canonical Canvas ID
        """
        validate_course.return_value = {'id': 1, 'sis_course_id': '100'}
        get_list_sections.return_value = []
        process_course('sis_course_id:100')
        unsync_from_canvas_and_reset_canvas_id.assert_called_once_with('100')
        unmark_course_as_official.assert_called_once_with(1)
        get_list_sections.assert_called_once_with(1)
        process_sections.assert_called_once_with([], 1)
        delete_course.assert_called_once_with(1)

    def test_process_course_skip_sis_updates(self, validate_course, get_list_sections, process_sections, delete_course, unsync_from_canvas_and_reset_canvas_id, unmark_course_as_official):
        """ skip sis updates if specified """
        validate_course.return_value = {'id': 1, 'sis_course_id': '100'}
        get_list_sections.return_value = []
        process_course('sis_course_id:100', skip_sis_updates=True)
        assert not unsync_from_canvas_and_reset_canvas_id.called
        assert not unmark_course_as_official.called
        get_list_sections.assert_called_once_with(1)
        process_sections.assert_called_once_with([], 1)
        delete_course.assert_called_once_with(1)

    def test_process_course_no_sis_id(self, validate_course, get_list_sections, process_sections, delete_course, unsync_from_canvas_and_reset_canvas_id, unmark_course_as_official):
        """
        skip CourseInstance updates if Canvas course has no associated SIS ID
        """
        validate_course.return_value = {'id': 1}
        get_list_sections.return_value = []
        process_course('sis_course_id:100')
        assert not unsync_from_canvas_and_reset_canvas_id.called
        unmark_course_as_official.assert_called_once_with(1)
        get_list_sections.assert_called_once_with(1)
        process_sections.assert_called_once_with([], 1)
        delete_course.assert_called_once_with(1)

    def test_process_course_blank_sis_id(self, validate_course, get_list_sections, process_sections, delete_course, unsync_from_canvas_and_reset_canvas_id, unmark_course_as_official):
        """
        skip CourseInstance updates if Canvas course has a blank SIS ID
        """
        validate_course.return_value = {'id': 1, 'sis_course_id': ''}
        get_list_sections.return_value = []
        process_course('sis_course_id:100')
        assert not unsync_from_canvas_and_reset_canvas_id.called
        unmark_course_as_official.assert_called_once_with(1)
        get_list_sections.assert_called_once_with(1)
        process_sections.assert_called_once_with([], 1)
        delete_course.assert_called_once_with(1)


@patch.multiple('canvas_course_site_wizard.management.commands.delete_canvas_courses',
                courses=DEFAULT)
class DeleteScriptValidateCourseHelperTestCase(TestCase):

    def test_course_found(self, courses, **kwargs):
        """ should return Canvas course dict if lookup id is found in Canvas """
        courses.get_single_course_courses.return_value.json.return_value = {'id': 1}
        return_value = validate_course('sis_course_id:100')
        self.assertEqual(return_value.get('id'), 1)

    def test_course_not_found(self, courses, **kwargs):
        """ should return None if lookup id is not found in Canvas """
        courses.get_single_course_courses.side_effect = CanvasAPIError
        return_value = validate_course('sis_course_id:100')
        self.assertIsNone(return_value)


@patch.multiple('canvas_course_site_wizard.management.commands.delete_canvas_courses',
                get_all_list_data=DEFAULT)
class DeleteScriptGetListSectionHelperTestCase(TestCase):

    def test_sections_found(self, get_all_list_data, **kwargs):
        """ should return list of sections if any found in Canvas """
        mock_section_list = [{'id': 1}]
        get_all_list_data.return_value = mock_section_list
        return_value = get_list_sections(1)
        self.assertEqual(return_value, mock_section_list)

    def test_sections_not_found(self, get_all_list_data, **kwargs):
        """ should return empty list if nothing found in Canvas """
        get_all_list_data.side_effect = CanvasAPIError
        return_value = get_list_sections(1)
        self.assertEqual(return_value, [])


@patch.multiple('canvas_course_site_wizard.management.commands.delete_canvas_courses',
                delete_enrollments_for_section=DEFAULT,
                delete_section=DEFAULT)
class DeleteScriptProcessSectionsHelperTestCase(TestCase):

    def test_no_sections(self, delete_enrollments_for_section, **kwargs):
        """ if there are no sections to process, no need to delete anything """
        mock_section_list = []
        process_sections(mock_section_list, 1)
        self.assertFalse(delete_enrollments_for_section.called)

    def test_multiple_sections(self, delete_enrollments_for_section, delete_section, **kwargs):
        """ if there are multiple sections to process, should delete each one """
        mock_section_list = [{'id': 1}, {'id': 2}]
        process_sections(mock_section_list, 1)
        self.assertEqual(delete_enrollments_for_section.call_count, 2)
        self.assertEqual(delete_section.call_count, 2)

    def test_bad_section(self, delete_enrollments_for_section, delete_section, **kwargs):
        """ if there are multiple sections to process but one is invalid, should still delete the good ones """
        mock_section_list = [{}, {'id': 1}]
        process_sections(mock_section_list, 1)
        self.assertEqual(delete_enrollments_for_section.call_count, 1)
        self.assertEqual(delete_section.call_count, 1)


@patch.multiple('canvas_course_site_wizard.management.commands.delete_canvas_courses',
                get_all_list_data=DEFAULT,
                enrollments=DEFAULT)
class DeleteScriptDeleteEnrollmentsForSectionHelperTestCase(TestCase):

    def test_multiple_enrollments(self, get_all_list_data, enrollments, **kwargs):
        """ if there are multiple enrollments to process, should delete each one """
        mock_canvas_enrollments = [{'id': 1, 'course_id': 1}, {'id': 2, 'course_id': 1}]
        get_all_list_data.return_value = mock_canvas_enrollments
        delete_enrollments_for_section(3, 1)
        self.assertEqual(enrollments.conclude_enrollment.call_count, 2)

    def test_no_enrollments(self, get_all_list_data, enrollments, **kwargs):
        """ if there are no enrollments to process, no need to delete anything """
        get_all_list_data.return_value = []
        delete_enrollments_for_section(3, 1)
        self.assertFalse(enrollments.conclude_enrollment.called)

    def test_error_fetching_enrollments(self, get_all_list_data, enrollments, **kwargs):
        """ no need to delete anything if enrollment list call fails """
        get_all_list_data.side_effect = CanvasAPIError
        delete_enrollments_for_section(3, 1)
        self.assertFalse(enrollments.conclude_enrollment.called)

    def test_bad_enrollment(self, get_all_list_data, enrollments, **kwargs):
        """ if there are multiple enrollments to process but one is invalid, should still delete the good ones """
        mock_canvas_enrollments = [{'id': 1, 'course_id': 1}, {'id': 2, 'course_id': 1}]
        get_all_list_data.return_value = mock_canvas_enrollments
        enrollments.conclude_enrollment.side_effect = [CanvasAPIError, '200']
        delete_enrollments_for_section(3, 1)
        self.assertEqual(enrollments.conclude_enrollment.call_count, 2)


@patch.multiple('canvas_course_site_wizard.management.commands.delete_canvas_courses',
                get_canvas_course_url=DEFAULT,
                CourseSite=DEFAULT)
class DeleteScriptUnmarkCourseAsOfficialHelperTestCase(TestCase):

    def test_delete_if_found(self, get_canvas_course_url, CourseSite, **kwargs):
        """ course site mapping should be deleted if found """
        get_canvas_course_url.return_value = 'http://something'
        course_mock = MagicMock(name='course_mock')
        CourseSite.objects.get.return_value = course_mock
        unmark_course_as_official(1)
        assert course_mock.delete.called


@patch.multiple('canvas_course_site_wizard.management.commands.delete_canvas_courses',
                get_course_data=DEFAULT)
class DeleteScriptUnsyncFromCanvasAndResetCanvasIdHelperTestCase(TestCase):

    def test_unsync_and_save(self, get_course_data, **kwargs):
        """
        course instance should be unsynced from canvas and saved
        with a null canvas_course_id field value
        """
        course_data_mock = MagicMock(name='course_data_mock')
        get_course_data.return_value = course_data_mock
        unsync_from_canvas_and_reset_canvas_id('100')
        assert course_data_mock.set_sync_to_canvas.called
        assert course_data_mock.save.called
        self.assertIsNone(course_data_mock.canvas_course_id)
