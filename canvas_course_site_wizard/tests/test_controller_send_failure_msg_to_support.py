from unittest import TestCase
from mock import patch, DEFAULT, ANY
from canvas_course_site_wizard.controller import send_failure_msg_to_support
from django.test.utils import override_settings

override_settings_dict = {
    'support_email_body_on_failure': 'Test message',
    'support_email_subject_on_failure': 'Test subject',
    'support_email_address': 'test@test.com',
    'from_email_address': 'sender@test.com',
    'environment': 'test'
}

@patch.multiple('canvas_course_site_wizard.controller', send_mail=DEFAULT)
class SendMailHelperTest(TestCase):

    def setUp(self):
        self.sis_course_id = "12345"
        self.user = "999"
        self.error_detail = "There was a problem in creating the course"

    @override_settings(CANVAS_EMAIL_NOTIFICATION=override_settings_dict)
    def test_send_failure_msg_to_support_invoked_with_correct_args(self,
                                                                   send_mail):
        """
        Test that send_mail is called with expected
        args passed into send_failure_msg_to_support
        """
        result = send_failure_msg_to_support(self.sis_course_id, self.user,
                                             self.error_detail)
        send_mail.assert_called_with(
            override_settings_dict['support_email_subject_on_failure'],
            override_settings_dict['support_email_body_on_failure'],
            override_settings_dict['from_email_address'],
            [override_settings_dict['support_email_address']],
            fail_silently=ANY
        )

    @override_settings(CANVAS_EMAIL_NOTIFICATION=override_settings_dict)
    def test_handling_of_send_mail_exception(self, send_mail):
        """
        Test to assert that an exception is raised by
        send_failure_msg_to_support, when the send_mail throws an exception
        """
        send_failure_msg_to_support(self.sis_course_id, self.user,
                                    self.error_detail)
        send_mail.side_effect = Exception
        self.assertRaises(Exception, send_failure_msg_to_support,
                          self.sis_course_id, self.user, self.error_detail)
