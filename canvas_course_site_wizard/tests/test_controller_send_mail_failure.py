from unittest import TestCase
from mock import patch, DEFAULT, ANY
from django.core import mail
from canvas_course_site_wizard.controller import send_failure_email
from django.test.utils import override_settings

import unittest


@patch.multiple('canvas_course_site_wizard.controller', send_mail = DEFAULT)


class SendMailFailureTest(TestCase):

    def setUp(self):
        self.sis_course_id = "12345"
        self.initiator_email = 'sender@test.com'
        self.subject = "Test subject"
        self.message = "Test message"
        self.to_address = ['test@test.com']
        self.from_address = 'sender@test.com'
        

    @override_settings(CANVAS_EMAIL_NOTIFICATION= {'support_email_address':'a','course_migration_failure_subject':'b','course_migration_failure_body':'c' ,'from_email_address': 'd'})
    def test_send_failure_email_invoked_with_correct_args(self, send_mail):
        """
        Test that send_failure_email is called with expected args passed into send_failure_email
        """

        result = send_failure_email(self.initiator_email, self.sis_course_id)
        send_mail.assertCalledWith(self.subject, self.message, self.from_address, self.to_address ,fail_silently=ANY)

    @override_settings(CANVAS_EMAIL_NOTIFICATION= {'support_email_address':'a','course_migration_failure_subject':'b','course_migration_failure_body':'c' ,'from_email_address': 'd'})
    def test_send_failure_email_on_exception(self, send_mail):
        """ Test to assert that an exception is raised when the send_mail throws an exception"""
        from_address = self.from_address
        send_failure_email(self.initiator_email, self.sis_course_id)
        send_mail.side_effect = Exception	
        self.assertRaises( Exception, send_failure_email, self.initiator_email, self.sis_course_id)
        
    