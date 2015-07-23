from selenium_tests.base_test_case import BaseSeleniumTestCase
from django.conf import settings

class BulkCreateBaseTestCase(BaseSeleniumTestCase):
    """
    Bulk Create base test case, all other tests will subclass this class
    """

    @classmethod
    def setUpClass(cls):
        """
        setup values for the tests
        """
        super(BulkCreateBaseTestCase, cls).setUpClass()
        cls.USERNAME = settings.SELENIUM_CONFIG.get('selenium_username')
        cls.PASSWORD = settings.SELENIUM_CONFIG.get('selenium_password')
        cls.BASE_URL = '%s/accounts/345/external_tools/1210' % settings.SELENIUM_CONFIG.get('base_url')

    @classmethod
    def tearDownClass(cls):
        super(BulkCreateBaseTestCase, cls).tearDownClass()



