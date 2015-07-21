from unittest import TestCase
from mock import Mock, patch
from canvas_course_site_wizard.mixins import CourseSiteCreationAllowedMixin
from django.core.exceptions import PermissionDenied


class CourseSiteCreationAllowedMixinTest(TestCase):
    longMessage = True

    def setUp(self):
        self.mixin = CourseSiteCreationAllowedMixin()
        self.request = Mock(name='RequestMock')

    @patch('canvas_course_site_wizard.mixins.super', create=True)
    @patch.object(CourseSiteCreationAllowedMixin, 'is_current_user_member_of_course_staff', return_value=True)
    @patch.object(CourseSiteCreationAllowedMixin, 'list_current_user_admin_roles_for_course', return_value=[])
    @patch.object(CourseSiteCreationAllowedMixin, 'get_object')
    def test_dispatch_calls_get_object_and_stores_value(self, get_object_mock, *args):
        """
        Ensure that if there was no object attribute set on mixin, a call to get_object
        is made and result is stored as attribute
        """
        self.mixin.object = None
        self.mixin.dispatch(self.request)
        get_object_mock.assert_called_once_with()
        self.assertEqual(self.mixin.object, get_object_mock.return_value)

    @patch('canvas_course_site_wizard.mixins.super', create=True)
    @patch.object(CourseSiteCreationAllowedMixin, 'get_object')
    @patch.object(CourseSiteCreationAllowedMixin, 'is_current_user_member_of_course_staff', return_value=False)
    @patch.object(CourseSiteCreationAllowedMixin, 'list_current_user_admin_roles_for_course', return_value=[])
    def test_dispatch_raises_permission_denied_when_not_staff_and_not_admin(self, *args):
        """
        If the user is neither a staff member nor a course admin, they should be denied
        """
        with self.assertRaises(PermissionDenied):
            self.mixin.dispatch(self.request)

    @patch.object(CourseSiteCreationAllowedMixin, 'get_object')
    @patch.object(CourseSiteCreationAllowedMixin, 'is_current_user_member_of_course_staff', return_value=True)
    @patch.object(CourseSiteCreationAllowedMixin, 'list_current_user_admin_roles_for_course', return_value=[])
    @patch('canvas_course_site_wizard.mixins.super', create=True)
    def test_dispatch_calls_super_when_staff_and_not_admin(self, super_mock, *args):
        self.mixin.dispatch(self.request)
        super_mock.assert_called()

    @patch.object(CourseSiteCreationAllowedMixin, 'get_object')
    @patch.object(CourseSiteCreationAllowedMixin, 'is_current_user_member_of_course_staff', return_value=False)
    @patch.object(CourseSiteCreationAllowedMixin, 'list_current_user_admin_roles_for_course', return_value=[('admin')])
    @patch('canvas_course_site_wizard.mixins.super', create=True)
    def test_dispatch_calls_super_when_admin_and_not_staff(self, super_mock, *args):
        self.mixin.dispatch(self.request)
        super_mock.assert_called()

    @patch.object(CourseSiteCreationAllowedMixin, 'get_object')
    @patch.object(CourseSiteCreationAllowedMixin, 'is_current_user_member_of_course_staff', return_value=True)
    @patch.object(CourseSiteCreationAllowedMixin, 'list_current_user_admin_roles_for_course', return_value=[('admin')])
    @patch('canvas_course_site_wizard.mixins.super', create=True)
    def test_dispatch_calls_super_when_admin_and_staff(self, super_mock, *args):
        self.mixin.dispatch(self.request)
        super_mock.assert_called()
