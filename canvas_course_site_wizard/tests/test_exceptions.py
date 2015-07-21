import unittest
from canvas_course_site_wizard.exceptions import RenderableExceptionWithDetails


class MockDetailedRenderable(RenderableExceptionWithDetails):
    display_text = 'A test exception {0}'
    status_code = 400


class RenderableExceptionTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_get_string_representation(self):
        """
        Tests that when logged or printed the RenderableExceptionWithDetails displays the expected information
        and that the display_text is properly formatted using the argument passed on instantiation
        """
        e = MockDetailedRenderable('with details')
        self.assertEqual('%s' % e, 'MockDetailedRenderable(status=%s, display_text=%s)' % (e.status_code, 'A test exception with details'))
