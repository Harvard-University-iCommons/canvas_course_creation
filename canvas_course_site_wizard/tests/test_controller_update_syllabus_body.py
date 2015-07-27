from unittest import TestCase
from mock import patch, DEFAULT, Mock

from canvas_course_site_wizard.controller import update_syllabus_body
from canvas_course_site_wizard.exceptions import NoTemplateExistsForSchool

canvas_course_id = 4321
sis_course_id = 123456
bulk_job_id = 44444
template_id = 1234
course_syllabus_body = '<b>Course Info</b>'
CourseInstanceMock = Mock(**{
    'objects.get.return_value': Mock(
        school=Mock(school_id='colgsas'),
        html_formatted_course_info=course_syllabus_body
    )
})


@patch.multiple(
    'canvas_course_site_wizard.controller',
    CourseInstance=CourseInstanceMock,
    get_default_template_for_school=DEFAULT,
    SDK_CONTEXT=DEFAULT,
    update_course=DEFAULT,
)
class UpdateSyllabusBodySingleCourseJobTest(TestCase):
    def setUp(self):
        self.course_job = Mock(
            sis_course_id=sis_course_id,
            bulk_job_id=None,
            canvas_course_id=canvas_course_id
        )

    def test_no_default_template(self, update_course, get_default_template_for_school, **kwargs):
        get_default_template_for_school.side_effect = NoTemplateExistsForSchool(sis_course_id)
        update_syllabus_body(self.course_job)
        assert not update_course.called

    @patch('canvas_course_site_wizard.controller.CanvasSchoolTemplate.objects.get')
    def test_default_template_include_course_info(self, template_mock, get_default_template_for_school, SDK_CONTEXT,
                                                  update_course, **kwargs):
        template_mock.return_value = Mock(include_course_info=True)
        get_default_template_for_school.return_value = Mock(template_id=template_id)
        update_syllabus_body(self.course_job)
        update_course.assert_called_with(
            SDK_CONTEXT,
            canvas_course_id,
            course_syllabus_body=course_syllabus_body
        )

    @patch('canvas_course_site_wizard.controller.CanvasSchoolTemplate.objects.get')
    def test_default_template_not_include_course_info(self, template_mock, update_course,
                                                      get_default_template_for_school, **kwargs):
        get_default_template_for_school.return_value = Mock(template_id=template_id)
        template_mock.return_value = Mock(include_course_info=False)
        update_syllabus_body(self.course_job)
        assert not update_course.called


@patch.multiple(
    'canvas_course_site_wizard.controller',
    CourseInstance=CourseInstanceMock,
    SDK_CONTEXT=DEFAULT,
    update_course=DEFAULT,
)
class UpdateSyllabusBodyBulkJobTest(TestCase):
    def setUp(self):
        self.course_job = Mock(
            sis_course_id=sis_course_id,
            bulk_job_id=bulk_job_id,
            canvas_course_id=canvas_course_id
        )

    @patch('canvas_course_site_wizard.controller.BulkCanvasCourseCreationJob.objects.get')
    def test_no_template(self, bulk_job_mock, update_course, **kwargs):
        bulk_job_mock.return_value = Mock(template_canvas_course_id=None)
        update_syllabus_body(self.course_job)
        assert not update_course.called

    @patch('canvas_course_site_wizard.controller.BulkCanvasCourseCreationJob.objects.get')
    @patch('canvas_course_site_wizard.controller.CanvasSchoolTemplate.objects.get')
    def test_template_include_course_info(self, template_mock, bulk_job_mock, SDK_CONTEXT, update_course, **kwargs):
        bulk_job_mock.return_value = Mock(template_canvas_course_id=template_id)
        template_mock.return_value = Mock(include_course_info=True)
        update_syllabus_body(self.course_job)
        update_course.assert_called_with(
            SDK_CONTEXT,
            canvas_course_id,
            course_syllabus_body=course_syllabus_body
        )

    @patch('canvas_course_site_wizard.controller.BulkCanvasCourseCreationJob.objects.get')
    @patch('canvas_course_site_wizard.controller.CanvasSchoolTemplate.objects.get')
    def test_template_not_include_course_info(self, template_mock, bulk_job_mock, SDK_CONTEXT, update_course, **kwargs):
        bulk_job_mock.return_value = Mock(template_canvas_course_id=template_id)
        template_mock.return_value = Mock(include_course_info=False)
        update_syllabus_body(self.course_job)
        assert not update_course.called
