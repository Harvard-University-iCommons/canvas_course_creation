from selenium_tests.bulk_create.base_test_case import BulkCreateBaseTestCase
from selenium_tests.bulk_create.page_objects.pin_page import LoginPage

class TestFlow(BulkCreateBaseTestCase):

    def test_course_selection(self):
        """
        Tests a user accessing the bulk create tool, they have to login first. Loggin in
        sends them to the bulk create index page. there they select a term (here we select
        term with value 1), then they select a course group (here we select a group with
        value 106 "Humanities" on icommons common), then they click the "create canvas sites" button.
        The button click sends them to the course selection page where they can select a template (here
        we choose "None") ans then we select 2 courses in the table at locations 5 and 6. We assert
        that the course selection page is loaded.
        """
        pin_page = LoginPage(self.driver)
        pin_page.get(self.BASE_URL)
        index_page = pin_page.login(self.USERNAME, self.PASSWORD)
        # select the first term
        index_page.select_term('1')
        # select the course group 105 (Humanities)
        index_page.select_course_group('106')
        course_selection_page = index_page.create_canvas_sites()
        # select the 'No Template' option
        course_selection_page.select_template('None')
        # select two courses from the datatable
        # we are not actually creating courses here, if we do
        # we'll need to change this
        course_selection_page.select_course('1')
        course_selection_page.select_course('2')
        # after we selected the template the 'Create' button should be enabled
        self.assertTrue(course_selection_page.is_create_selected_button_enabled(), "create selection button is not enabled")

