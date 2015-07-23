"""
To run these tests from the command line in a local VM, you'll need to set up the environment:
> export PYTHONPATH=/home/vagrant/icommons_lti_tools
> export DJANGO_SETTINGS_MODULE=icommons_lti_tools.settings.local
> sudo apt-get install xvfb
> python selenium_tests/regression_tests.py

Or for just one set of tests, for example:
> python selenium_tests/manage_people/mp_test_search.py

In PyCharm, if xvfb is installed already, you can run them through the Python unit test run config
(make sure the above environment settings are included)
"""

import unittest
import time
from selenium_tests.bulk_create.bc_test_flow import TestFlow

import HTMLTestRunner


dateTimeStamp = time.strftime('%Y%m%d_%H_%M_%S')
buf = file("TestReport" + "_" + dateTimeStamp + ".html", 'wb')
runner = HTMLTestRunner.HTMLTestRunner(
    stream=buf,
    title='Test the Report',
    description='Result of tests'
)

# bulk create - test the flow of the app from login to course selection
bulk_create_flow_test = unittest.TestLoader().loadTestsFromTestCase(TestFlow)

# create a test suite combining search_tests and results_page_tests
smoke_tests = unittest.TestSuite([bulk_create_flow_test])

# run the suite
runner.run(smoke_tests)

