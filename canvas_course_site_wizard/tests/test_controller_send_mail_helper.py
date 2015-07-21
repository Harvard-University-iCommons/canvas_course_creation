from unittest import TestCase
from mock import patch, DEFAULT, ANY
from django.core import mail
from canvas_course_site_wizard.controller import send_email_helper
from django.test.utils import override_settings


import unittest


@patch.multiple('canvas_course_site_wizard.controller', send_mail = DEFAULT)


class SendMailHelperTest(TestCase):
    longMessage = True

    def setUp(self):
        self.subject = "Test subject"
        self.message = "Test message"
        self.to_address = ['test@test.com']
        self.from_address = 'sender@test.com'

    @override_settings(CANVAS_EMAIL_NOTIFICATION= {'from_email_address':'xyz'})
    def test_send_mail_invoked_with_correct_args(self, send_mail):
        """
        Test that send_mail is called with expected args passed into send_email_helper
        """
    	from_address = self.from_address
        result = send_email_helper(self.subject, self.message, self.to_address)
        send_mail.assertCalledWith(self.subject, self.message, from_address, self.to_address ,fail_silently=ANY)

    @override_settings(CANVAS_EMAIL_NOTIFICATION= {'from_email_address':'xyz'})
    def test_send_mail_on_exception(self, send_mail):
        """ Test to assert that an exception is raised when the send_mail throws an exception"""
        from_address = self.from_address
        send_mail.side_effect = Exception	
        self.assertRaises( Exception, send_email_helper, self.subject, self.message, self.to_address)
    
    
