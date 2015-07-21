from unittest import TestCase
from mock import Mock, patch
from canvas_course_site_wizard.models import SISCourseData
from canvas_course_site_wizard.mixins import CourseDataPermissionsMixin


class CourseDataPermissionsMixinTest(TestCase):
    longMessage = True

    def setUp(self):
        self.course_data = Mock(
            spec=SISCourseData,
            pk=1234,
            school_code='colgsas',
        )
        self.mixin = CourseDataPermissionsMixin()
        self.mixin.request = Mock(
            session={},
            user=Mock(username='12345'),
        )
        self.mixin.object = self.course_data

    def test_is_current_user_member_of_course_staff_handles_no_course_object(self):
        """
        Ensure that if there was no object attribute set on mixin, a call to get_object
        is made and result is stored as attribute
        """
        self.mixin.object = None
        self.mixin.get_object = Mock(name="CourseDataMock")
        self.mixin.is_current_user_member_of_course_staff()
        self.mixin.get_object.assert_called_once_with()
        self.assertEqual(self.mixin.object, self.mixin.get_object.return_value)

    def test_is_current_user_member_of_course_staff_when_no_user_groups_in_session(self):
        """
        This test is mainly to make sure that default value is provided for session call so that a dict
        key exception is not raised
        """
        self.mixin.request.session = {}
        response = self.mixin.is_current_user_member_of_course_staff()
        self.assertFalse(response, 'User with no groups defined in session should return False')

    def test_is_current_user_member_of_course_staff_when_user_member_of_no_groups(self):
        self.mixin.request.session = {'USER_GROUPS': []}
        response = self.mixin.is_current_user_member_of_course_staff()
        self.assertFalse(response, 'User with no groups should result return False')

    def test_is_current_user_member_of_course_staff_when_user_member_of_non_staff_course_group(self):
        course_instance_id = self.course_data.pk
        self.mixin.request.session = {'USER_GROUPS': ['ScaleCourseStudent:%d' % course_instance_id]}
        response = self.mixin.is_current_user_member_of_course_staff()
        self.assertFalse(response, 'Non-teaching staff should result return False')

    def test_is_current_user_member_of_course_staff_when_user_member_of_another_course_staff(self):
        course_instance_id = self.course_data.pk
        self.mixin.request.session = {'USER_GROUPS': ['ScaleCourseStaff:%d' % (course_instance_id - 1)]}
        response = self.mixin.is_current_user_member_of_course_staff()
        self.assertFalse(response, 'Teaching staff for a different course should return False')

    def test_is_current_user_member_of_course_staff_when_user_member_of_course_staff(self):
        course_instance_id = self.course_data.pk
        self.mixin.request.session = {'USER_GROUPS': ['ScaleCourseStaff:%d' % course_instance_id]}
        response = self.mixin.is_current_user_member_of_course_staff()
        self.assertTrue(response, 'Teaching staff for course should return True')

    @patch('canvas_course_site_wizard.mixins.admins')
    def test_list_current_user_admin_roles_for_course_handles_no_course_object(self, sdk_admins_mock):
        """
        Ensure that if there was no object attribute set on mixin, a call to get_object
        is made and result is stored as attribute
        """
        self.mixin.object = None
        self.mixin.get_object = Mock(name="CourseDataMock")
        sdk_admins_mock.list_account_admins.return_value.json.return_value = []
        self.mixin.list_current_user_admin_roles_for_course()
        self.mixin.get_object.assert_called_once_with()
        self.assertEqual(self.mixin.object, self.mixin.get_object.return_value)

    @patch('canvas_course_site_wizard.mixins.SDK_CONTEXT')
    @patch('canvas_course_site_wizard.mixins.admins')
    def test_list_current_user_admin_roles_for_course_sdk_method_called_with_context(self, sdk_admins_mock, context_mock):
        """ Test that admin sdk method was called with context keyword parameter """
        sdk_admins_mock.list_account_admins.return_value.json.return_value = []
        self.mixin.list_current_user_admin_roles_for_course()
        args, kwargs = sdk_admins_mock.list_account_admins.call_args
        self.assertEqual(kwargs.get('request_ctx'), context_mock)

    @patch('canvas_course_site_wizard.mixins.admins')
    def test_list_current_user_admin_roles_for_course_sdk_method_called_with_course_code(self, sdk_admins_mock):
        """ Test that admin sdk method was called with expected account_id keyword parameter """
        expected_account_id = '%s' % self.course_data.school_code
        sdk_admins_mock.list_account_admins.return_value.json.return_value = []
        self.mixin.list_current_user_admin_roles_for_course()
        args, kwargs = sdk_admins_mock.list_account_admins.call_args
        self.assertEqual(kwargs.get('account_id'), 'sis_account_id:school:%s' % expected_account_id)

    @patch('canvas_course_site_wizard.mixins.admins')
    def test_list_current_user_admin_roles_for_course_finds_single_matching_users(self, sdk_admins_mock):
        """
        If the admin list contains the current user, the method should return the user object from the list.
        """
        mock_user_to_find = {"user": {"id": 2, "sis_user_id": self.mixin.request.user.username}}
        mock_user_list = [mock_user_to_find]
        sdk_admins_mock.list_account_admins.return_value.json.return_value = mock_user_list
        return_value = self.mixin.list_current_user_admin_roles_for_course()
        self.assertEqual(return_value[0], mock_user_to_find)
        self.assertEqual(len(return_value), 1)

    @patch('canvas_course_site_wizard.mixins.admins')
    def test_list_current_user_admin_roles_for_course_finds_multiple_matching_users(self, sdk_admins_mock):
        """
        If the admin list contains multiple instances of the current user (e.g. with different roles),
        the method should return all of the valid user objects from the list.
        """
        mock_user_to_find_first_instance = {
            "role": "SchoolLiaison", "user": {"id": 2, "sis_user_id": self.mixin.request.user.username}
        }
        mock_user_to_find_second_instance = mock_user_to_find_first_instance.copy()
        mock_user_to_find_second_instance['role'] = "AccountAdmin"
        mock_user_list = [mock_user_to_find_first_instance, mock_user_to_find_second_instance]
        sdk_admins_mock.list_account_admins.return_value.json.return_value = mock_user_list
        return_value = self.mixin.list_current_user_admin_roles_for_course()
        self.assertEqual(return_value[0], mock_user_to_find_first_instance)
        self.assertEqual(return_value[1], mock_user_to_find_second_instance)
        self.assertEqual(len(return_value), 2)

    @patch("canvas_course_site_wizard.mixins.admins")
    def test_list_current_user_admin_roles_for_course_no_matching_users(self, sdk_admins_mock):
        """
        If the admin list does not contain the current user, the method should return an empty list.
        """
        mock_user_list = []
        sdk_admins_mock.list_account_admins.return_value.json.return_value = mock_user_list
        return_value = self.mixin.list_current_user_admin_roles_for_course()
        self.assertEqual(return_value, [])
