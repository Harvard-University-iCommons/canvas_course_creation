from unittest import TestCase
from mock import patch, DEFAULT, ANY
from canvas_course_site_wizard.controller import get_canvas_user_profile
import logging
import unittest

# Get an instance of a logger
logger = logging.getLogger(__name__)

@patch.multiple('canvas_course_site_wizard.controller', SDK_CONTEXT=DEFAULT, get_user_profile=DEFAULT)

class GetCanvasUserProfileTest(TestCase):
    longMessage = True

    def setUp(self):
        self.user_id = "12345678"

    def test_get_canvas_user_profile_method_called_with_right_params(self, SDK_CONTEXT, get_user_profile):
        """
        Test get_user_profile is called with expected args
        """
        get_user_profile.return_value = DEFAULT
        result = get_canvas_user_profile(self.user_id)
        get_user_profile.assert_called_with(request_ctx=SDK_CONTEXT, user_id='sis_user_id:%s' % self.user_id)

    def test_when_get_user_profile_method_raises_exception(self, SDK_CONTEXT, get_user_profile):
        """
        Test to assert that an exception is raised when the get_user_profile method throws an exception
        """
        get_user_profile.side_effect = Exception
        self.assertRaises(Exception, get_canvas_user_profile, self.user_id)
