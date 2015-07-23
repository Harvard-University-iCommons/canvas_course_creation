
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_tests.bulk_create.page_objects.base_page_object import BulkCreateBasePageObject
from selenium.webdriver.support.ui import Select

class CourseSelectionPageLocators(object):
    # List of WebElements found on course selection page
    # Not all HTML tags are found here, but on a need basis
    COURSE_INSTANCE_TABLE = (By.ID, "courseInstanceDT")
    TEMPLATE_SELECT_DROPDOWN = (By.ID, "templateSelect")
    CREATE_SELECTED_BUTTON = (By.XPATH, "//button[@type='button']")


class CourseSelectionPageObject(BulkCreateBasePageObject):
    """
    bulk create step 1, select the school and term page
    """

    def is_loaded(self):
        """ determine if the page loaded by looking for a specific element on the page """
        # frame context stickiness is a bit flaky for some reason; make sure we're in the tool_content frame context
        # before checking for elements on the expected
        self.focus_on_tool_frame()
        try:
            self.find_element(*CourseSelectionPageLocators.COURSE_INSTANCE_TABLE)
        except NoSuchElementException:
            return False
        return True

    def select_template(self, template):
        """ select a template from the template element """
        Select(self.find_element(*CourseSelectionPageLocators.TEMPLATE_SELECT_DROPDOWN)).select_by_value(template)

    def select_course(self, checkbox_num):
        """ select a course from the course datatable element by checkbox number """
        self.find_element_by_xpath("(//input[@type='checkbox'])["+checkbox_num+"]").click()

    def is_create_selected_button_enabled(self):
        """
        check to see if the create selected button is enabled. If a template is selected the button should be enabled.
        :returns boolean
        """
        created_selected_button = self.find_element(*CourseSelectionPageLocators.CREATE_SELECTED_BUTTON)
        return created_selected_button.is_enabled()
