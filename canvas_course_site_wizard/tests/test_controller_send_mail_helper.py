from unittest import TestCase
from mock import patch, DEFAULT, ANY
from canvas_course_site_wizard.controller import send_email_helper
from django.test.utils import override_settings

override_settings_dict = {
    'from_email_address': 'sender@test.com',
}


@patch.multiple('canvas_course_site_wizard.controller', send_mail=DEFAULT)
class SendMailHelperTest(TestCase):
    longMessage = True

    def setUp(self):
        self.subject = "Test subject"
        self.message = "Test message"
        self.to_address = ['test@test.com']

    @override_settings(CANVAS_EMAIL_NOTIFICATION=override_settings_dict)
    def test_send_mail_invoked_with_correct_args(self, send_mail):
        """
        Test that send_mail is called with expected
        args passed into send_email_helper
        """
        result = send_email_helper(self.subject, self.message, self.to_address)
        send_mail.assert_called_with(
            self.subject,
            self.message,
            override_settings_dict['from_email_address'],
            self.to_address,
            fail_silently=ANY
        )

    @override_settings(CANVAS_EMAIL_NOTIFICATION=override_settings_dict)
    def test_send_mail_on_exception(self, send_mail):
        """
        Test to assert that an exception is raised
        when the send_mail throws an exception
        """
        send_mail.side_effect = Exception
        self.assertRaises(Exception, send_email_helper, self.subject,
                          self.message, self.to_address)
