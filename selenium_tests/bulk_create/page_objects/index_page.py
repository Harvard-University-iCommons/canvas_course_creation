"""
This file models some of the page objects on the Manage People Search Page.  (find_user.html)
"""
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_tests.bulk_create.page_objects.base_page_object import BulkCreateBasePageObject
from selenium_tests.bulk_create.page_objects.course_selection_page import CourseSelectionPageObject

from selenium.webdriver.support.ui import Select

class IndexPageLocators(object):
    # List of WebElements found on Manage People Search Page (Locators)
    # Not all HTML tags are found here, but on a need basis
    TERM_SELECT_DROPDOWN = (By.ID, "termSelect")
    CREATE_CANVAS_SITES_BUTTON = (By.ID, "createSitesButton")
    COURSE_GROUP_DROPDOWN = (By.ID, "courseGroupSelect")
    DEPARTMENT_DROPDOWN = (By.ID, "departmentSelect")


class IndexPageObject(BulkCreateBasePageObject):
    """
    The landing page of the bulk create tool
    """

    def is_loaded(self):
        """ determine if the page loaded by looking for a specific element on the page """

        self.focus_on_tool_frame()
        try:
            self.find_element(*IndexPageLocators.TERM_SELECT_DROPDOWN)
        except NoSuchElementException:
            return False

        return True

    def select_term(self, term):
        """ select the term element and set the value to the term param """
        self.focus_on_tool_frame()
        Select(self.find_element(*IndexPageLocators.TERM_SELECT_DROPDOWN)).select_by_value(term)

    def select_department(self, department):
        """ select the department element and set the value to the department param """
        self.focus_on_tool_frame()
        Select(self.find_element(*IndexPageLocators.DEPARTMENT_DROPDOWN)).select_by_value(department)

    def select_course_group(self, course_group):
        """ select the course_group element and set the value to the course_group param """
        self.focus_on_tool_frame()
        Select(self.find_element(*IndexPageLocators.COURSE_GROUP_DROPDOWN)).select_by_value(course_group)

    def create_canvas_sites(self):
        """ select the create_canvas_site button element and click it
        :returns CourseSelectionPageObject
        """
        self.focus_on_tool_frame()
        self.find_element(*IndexPageLocators.CREATE_CANVAS_SITES_BUTTON).click()
        return CourseSelectionPageObject(self._driver)


