from mock import Mock, MagicMock, patch, DEFAULT
from unittest import TestCase
from canvas_course_site_wizard.models import SISCourseDataMixin


class SISCourseDataStub(SISCourseDataMixin):
    """ An implementation of the course data mixin used for testing """
    course = MagicMock(registrar_code='FAS1234', school_id='fas')
    term = MagicMock()
    sites = MagicMock()
    sub_title = None
    save = Mock(return_value=DEFAULT)


class SISCourseDataMixinTest(TestCase):

    def setUp(self):
        self.course_data = SISCourseDataStub()
        self.isites_base_url = 'http://isites_base_url/'
        self.sync_flag = '1'

    def get_sync_to_canvas_save_mock(self):
        save_mock = Mock(return_value=DEFAULT)
        return save_mock

    def get_external_site_mock(self):
        return Mock(name='external_course_site', site_type_id='external', external_id='http://my.external.site')

    def get_isite_site_mock(self):
        return Mock(name='isite_course_site', site_type_id='isite', external_id='k12345')

    def test_sis_term_id_returns_string(self):
        """ Test that result of sis_term_id property is string result of meta_term_id call """
        term_id = 'formatted term id string'
        self.course_data.term.meta_term_id.return_value = term_id
        result = self.course_data.sis_term_id
        self.assertEqual(result, term_id)

    def test_sis_term_id_returns_none(self):
        """ Test that result of sis_term_id property is none result of meta_term_id call """
        self.course_data.term.meta_term_id.return_value = None
        result = self.course_data.sis_term_id
        self.assertEqual(result, None)

    def test_sis_account_id_returns_course_group_key_if_course_groups(self):
        """
        Test that result of sis_account_id is formatted primary key of first course group
        when there is at least one associated course group.
        """
        course_group_pk = 12345
        self.course_data.course.course_groups.count.return_value = 1
        self.course_data.course.course_groups.first.return_value = Mock(pk=course_group_pk)
        result = self.course_data.sis_account_id
        self.assertEqual(result, 'coursegroup:%s' % course_group_pk)

    def test_sis_account_id_returns_course_group_key_if_course_groups_and_departments(self):
        """
        Test that result of sis_account_id is formatted primary key of first course group
        when there is at least one associated course group, as well as departments.
        """
        course_group_pk = 12345
        self.course_data.course.course_groups.count.return_value = 1
        self.course_data.course.departments.count.return_value = 1
        self.course_data.course.course_groups.first.return_value = Mock(pk=course_group_pk)
        result = self.course_data.sis_account_id
        self.assertEqual(result, 'coursegroup:%s' % course_group_pk)

    def test_sis_account_id_returns_department_key_if_departments_and_no_course_groups(self):
        """
        Test that result of sis_account_id is formatted primary key of first department
        when there is at least one associated departments, but no course groups.
        """
        department_pk = 54321
        self.course_data.course.course_groups.count.return_value = 0
        self.course_data.course.departments.count.return_value = 1
        self.course_data.course.departments.first.return_value = Mock(pk=department_pk)
        result = self.course_data.sis_account_id
        self.assertEqual(result, 'dept:%s' % department_pk)

    def test_sis_account_id_returns_school_key_if_no_departments_and_no_course_groups(self):
        """
        Test that result of sis_account_id is formatted pk of associated school if there are
        no associated departments and no course groups.
        """
        school_id = self.course_data.course.school_id
        self.course_data.course.course_groups.count.return_value = 0
        self.course_data.course.departments.count.return_value = 0
        result = self.course_data.sis_account_id
        self.assertEqual(result, 'school:%s' % school_id)

    def test_course_code_returns_short_title_if_exists(self):
        """ Test that result of the course code is the short_title field of the course data object """
        short_title = 'A short course title'
        self.course_data.short_title = short_title
        result = self.course_data.course_code
        self.assertEqual(result, short_title)

    def test_course_code_returns_short_title_if_exists_and_registrar_code_display_exists(self):
        """
        Test that result of the course code is the short_title field of the course data object even
        if the associated course has a registrar_code_display field.
        """
        short_title = 'A short course title'
        self.course_data.short_title = short_title
        self.course_data.course.registrar_code_display = 'a display code'
        result = self.course_data.course_code
        self.assertEqual(result, short_title)

    def test_course_code_returns_registrar_code_display_if_exists_and_no_short_title(self):
        """
        Test that result of the course code is the registrar_code_display field of the associated course
        if the course data object does not have a short_title.
        """
        registrar_code_display = 'display-code-for-registrar'
        self.course_data.course.registrar_code_display = registrar_code_display
        self.course_data.short_title = None
        result = self.course_data.course_code
        self.assertEqual(result, registrar_code_display)

    def test_course_code_returns_registrar_code_if_no_short_title_and_no_registrar_display_code(self):
        """
        Test that result of the course code is the registrar_code field of the associated course if
        the course data object does not have a short_title and the course does not have a
        registrar_code_display field.
        """
        registrar_code = 'registrar-code'
        self.course_data.course.registrar_code_display = None
        self.course_data.short_title = None
        self.course_data.course.registrar_code = registrar_code
        result = self.course_data.course_code
        self.assertEqual(result, registrar_code)

    def test_course_name_returns_title_if_exists(self):
        """ Test that result of the course_name property is the course data object title. """
        title = 'course title'
        self.course_data.title = title
        result = self.course_data.course_name
        self.assertEqual(result, title)

    def test_course_name_returns_course_code_if_no_title(self):
        """ Test that result of the course_name property is the course_code property if no title exists. """
        self.course_data.title = None
        course_code = 'a sample course code'
        with patch.object(SISCourseDataStub, 'course_code', course_code):
            result = self.course_data.course_name
        self.assertEqual(result, course_code)

    def test_course_name_appends_sub_title_to_title_if_exists(self):
        """ Test that a subtitle is appended to an existing title if exists. """
        title = 'course title'
        sub_title = 'course sub_title'
        self.course_data.title = title
        self.course_data.sub_title = sub_title
        result = self.course_data.course_name
        self.assertEqual(result, '%s: %s' % (title, sub_title))

    def test_course_name_appends_sub_title_to_course_code_if_exists(self):
        """ Test that a subtitle is appended to the course_code if exists and no title exists. """
        self.course_data.title = None
        sub_title = 'course sub_title'
        self.course_data.sub_title = sub_title
        course_code = 'a sample course code'
        with patch.object(SISCourseDataStub, 'course_code', course_code):
            result = self.course_data.course_name
        self.assertEqual(result, '%s: %s' % (course_code, sub_title))

    def test_primary_section_name_formats_school_id_and_course_code(self):
        """
        Test that the primary section name is a formatted string based on school id and
        course_code properties.
        """
        course_code = 'a sample course code'
        school_id = self.course_data.course.school_id
        with patch.object(SISCourseDataStub, 'course_code', course_code):
            result = self.course_data.primary_section_name()
        self.assertEqual(result, '%s %s' % (school_id.upper(), course_code))

    def test_school_code_returns_school_id(self):
        """ Test that result of the school_code property is associated school id. """
        school_id = self.course_data.course.school_id
        result = self.course_data.school_code
        self.assertEqual(result, school_id)

    def test_set_sync_to_canvas_updates_record(self, ):
        '''
        Assert that the set_sync_to_canvas method updates record with correct value
        '''
        self.sync_to_canvas= '0'
        self.course_data.save = self.get_sync_to_canvas_save_mock()
        result = self.course_data.set_sync_to_canvas(self.sync_flag)
        self.assertEqual(result.sync_to_canvas, self.sync_flag)

    def test_set_sync_to_canvas_does_not_return_none(self):
        '''
        Assert that the set_sync_to_canvas method doesn't return None
        '''
        result = self.course_data.set_sync_to_canvas(self.sync_flag)
        self.assertNotEqual(result,None)

    def test_set_sync_to_canvas_calls_save(self):
        '''
        Assert that the set_sync_to_canvas calls save method
        '''
        self.course_data.save = self.get_sync_to_canvas_save_mock()
        result = self.course_data.set_sync_to_canvas(self.sync_flag)
        self.course_data.save.assert_called()
      
    def test_set_sync_to_canvas_calls_save_with_correct_params(self):
        '''
        Assert that the set_sync_to_canvas calls save method with correct params
        '''
        self.course_data.save = self.get_sync_to_canvas_save_mock()
        result = self.course_data.set_sync_to_canvas(self.sync_flag)
        self.course_data.save.assert_called_with(update_fields=['sync_to_canvas'])
      
    def test_set_sync_to_canvas_returns_SISCourseDataMixin_object(self):
        '''
        Assert that the set_sync_to_canvas method returns object of type SISCourseDataMixin
        '''
        self.course_data.save = self.get_sync_to_canvas_save_mock()
        result = self.course_data.set_sync_to_canvas(self.sync_flag)
        self.assertIsInstance(result, SISCourseDataMixin, 'Incorrect object type')

    def test_get_official_course_site_url_filters_on_official_site(self):
        """ Ensure that filter is called """
        self.course_data.get_official_course_site_url()
        self.course_data.sites.filter.assert_called_once_with(sitemap__map_type_id='official')

    def test_get_official_course_site_url_returns_none_if_no_official_sites(self):
        """ If course has no official sites, expect None """
        self.course_data.sites.filter.return_value = []
        res = self.course_data.get_official_course_site_url()
        self.assertIsNone(res)

    def test_get_official_course_site_url_returns_external_site(self):
        """ If official course site is external, make sure the url returned is based on external url """
        external_site_mock = self.get_external_site_mock()
        self.course_data.sites.filter.return_value = [external_site_mock]
        res = self.course_data.get_official_course_site_url()
        self.assertEqual(res, external_site_mock.external_id)

    def test_get_official_course_site_url_returns_isite_url(self):
        """ If official course site is an isite, make sure the url returned is based on isite base and keyword """
        isite_site_mock = self.get_isite_site_mock()
        self.course_data.sites.filter.return_value = [isite_site_mock]
        with patch('canvas_course_site_wizard.models.settings.ISITES_LMS_URL', self.isites_base_url):
            res = self.course_data.get_official_course_site_url()
        self.assertEqual(res, self.isites_base_url + isite_site_mock.external_id)

    def test_get_official_course_site_url_returns_first_url_when_isite(self):
        """ If the first official course site added was an isite, make sure that's the url returned """
        isite_site_mock = self.get_isite_site_mock()
        external_site_mock = self.get_external_site_mock()
        self.course_data.sites.filter.return_value = [isite_site_mock, external_site_mock]
        with patch('canvas_course_site_wizard.models.settings.ISITES_LMS_URL', self.isites_base_url):
            res = self.course_data.get_official_course_site_url()
        self.assertEqual(res, self.isites_base_url + isite_site_mock.external_id)

    def test_get_official_course_site_url_returns_first_url_when_external(self):
        """ If the first official course site is external, make sure that's the url returned """
        isite_site_mock = self.get_isite_site_mock()
        external_site_mock = self.get_external_site_mock()
        self.course_data.sites.filter.return_value = [external_site_mock, isite_site_mock]
        res = self.course_data.get_official_course_site_url()
        self.assertEqual(res, external_site_mock.external_id)

    @patch.multiple('canvas_course_site_wizard.models', CourseSite=DEFAULT, SiteMap=DEFAULT, SiteMapType=DEFAULT)
    def test_set_official_course_site_url_creates_course_site_row(self, CourseSite, SiteMap, SiteMapType):
        """ Make sure setting official course site creates a CourseSite row """
        site_url = 'http://my.site.url'
        self.course_data.set_official_course_site_url(site_url)
        CourseSite.objects.create.assert_called_once_with(site_type_id='external', external_id=site_url)

    @patch.multiple('canvas_course_site_wizard.models', CourseSite=DEFAULT, SiteMap=DEFAULT, SiteMapType=DEFAULT)
    def test_set_official_course_site_url_creates_site_map_row(self, CourseSite, SiteMap, SiteMapType):
        """ Make sure setting official course site creates a SiteMap row """
        site_url = 'http://my.site.url'
        self.course_data.set_official_course_site_url(site_url)
        SiteMap.objects.create.assert_called_once_with(course_instance=self.course_data,
                                                       course_site=CourseSite.objects.create.return_value,
                                                       map_type=SiteMapType.objects.get.return_value)

    @patch.multiple('canvas_course_site_wizard.models', CourseSite=DEFAULT, SiteMap=DEFAULT, SiteMapType=DEFAULT)
    def test_set_official_course_site_url_returns_newly_created_course_site_row(self, CourseSite, SiteMap, SiteMapType):
        """ Make sure setting official course site returns CouresSite row """
        site_url = 'http://my.site.url'
        res = self.course_data.set_official_course_site_url(site_url)
        self.assertEqual(res, CourseSite.objects.create.return_value)
