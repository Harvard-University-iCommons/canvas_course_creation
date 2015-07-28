from unittest import TestCase
from mock import patch, DEFAULT, ANY
from canvas_course_site_wizard.controller import send_failure_email
from django.test.utils import override_settings

override_settings_dict = {
    'course_migration_failure_subject': 'Test subject',
    'course_migration_failure_body': 'Test message',
    'support_email_address': 'test@test.com',
    'from_email_address': 'sender@test.com',
}


@patch.multiple('canvas_course_site_wizard.controller', send_mail=DEFAULT)
class SendMailFailureTest(TestCase):
    def setUp(self):
        self.sis_course_id = "12345"
        self.initiator_email = 'sender@test.com'

    @override_settings(CANVAS_EMAIL_NOTIFICATION=override_settings_dict)
    def test_send_failure_email_invoked_with_correct_args(self, send_mail):
        """
        Test that send_failure_email is called with expected
        args passed into send_failure_email
        """
        result = send_failure_email(self.initiator_email, self.sis_course_id)
        send_mail.assert_called_with(
            override_settings_dict['course_migration_failure_subject'],
            override_settings_dict['course_migration_failure_body'],
            override_settings_dict['from_email_address'],
            [
                override_settings_dict['from_email_address'],
                override_settings_dict['support_email_address']
            ],
            fail_silently=ANY
        )

    @override_settings(CANVAS_EMAIL_NOTIFICATION=override_settings_dict)
    def test_send_failure_email_on_exception(self, send_mail):
        """
        Test to assert that an exception is raised when the
        send_mail throws an exception
        """
        send_failure_email(self.initiator_email, self.sis_course_id)
        send_mail.side_effect = Exception
        self.assertRaises(Exception, send_failure_email, self.initiator_email,
                          self.sis_course_id)
