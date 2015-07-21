from unittest import TestCase
from mock import patch
from canvas_course_site_wizard.controller import get_canvas_course_url


@patch.dict('canvas_course_site_wizard.controller.settings.CANVAS_SITE_SETTINGS',
            {'base_url': 'https://icommons.canvas.harvard.edu/'})
class GetCanvasCourseURLTest(TestCase):
    """
    This test class should live in the same project as the get_canvas_course_url() utility method.
    """

    def setUp(self):
        self.sis_course_id = 123456
        self.canvas_course_id = 123
        self.override_url = 'https://tlt.harvard.canvas.com/'
        # This setting should match the one used in the @path.dict call for the class (see above)
        self.test_base_url = 'https://icommons.canvas.harvard.edu/'

    # no id, both ids, one id and the other, override URL, base URL

    def test_canvas_id(self):
        """
        Tests whether the expected URL is built on the Canvas ID passed to the utility method.
        """
        test_url = get_canvas_course_url(canvas_course_id=self.canvas_course_id)
        self.assertEqual(test_url, '%scourses/%s' % (self.test_base_url, self.canvas_course_id))

    def test_sis_id(self):
        """
        Tests whether the expected URL is built on the SIS course ID passed to the utility method.
        """
        test_url = get_canvas_course_url(sis_course_id=self.sis_course_id)
        self.assertEqual(test_url, '%scourses/sis_course_id:%s' % (self.test_base_url, self.sis_course_id))

    def test_both_ids_as_arguments(self):
        """
        Tests whether the URL built defaults as expected to the Canvas ID passed to the utility method,
        even when an SIS course ID is also provided.
        """
        test_url = get_canvas_course_url(canvas_course_id=self.canvas_course_id, sis_course_id=self.sis_course_id)
        self.assertEqual(test_url, '%scourses/%s' % (self.test_base_url, self.canvas_course_id))

    def test_no_id(self):
        """
        Tests that if no ID is passed to the utility method it returns None, even if the URL parameter are provided.
        """
        test_url = get_canvas_course_url(override_base_url=self.override_url)
        self.assertIsNone(test_url)

    def test_override_url(self):
        """
        Tests whether the expected URL is built on the override URL if it is passed to the utility method.
        """
        test_url = get_canvas_course_url(canvas_course_id=self.canvas_course_id, override_base_url=self.override_url)
        self.assertEqual(test_url, '%scourses/%s' % (self.override_url, self.canvas_course_id))
        # If for some reason the patched base URL and the override URL are equal, this assertion should catch it
        self.assertNotEqual(test_url, '%scourses/%s' % (self.test_base_url, self.canvas_course_id))
