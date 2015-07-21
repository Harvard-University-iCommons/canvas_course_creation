from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.test import TestCase

from mock import patch

from canvas_course_site_wizard.exceptions import MultipleDefaultTemplatesExistForSchool, NoTemplateExistsForSchool
from canvas_course_site_wizard.models_api import (
    get_default_template_for_school,
    get_courses_for_term,
    get_bulk_job_records_for_term,
    select_courses_for_bulk_create,
    get_course_generation_data_for_sis_course_id
)
from canvas_course_site_wizard.models import CanvasSchoolTemplate
from setup_bulk_jobs import create_jobs


class ModelsApiTest(TestCase):
    longMessage = True

    def setUp(self):
        self.school_id = 'fas'
        self.template_id = 123456
        self.term_id = 4545
        self.sis_course_id = 12345678
        self.bulk_job_id = 215
        self.course_job_id = 1475
        create_jobs(self.school_id, self.term_id)

    def test_single_template_exists_for_school(self):
        """ Data api method should return the template_id for a given school that has a matching row """
        CanvasSchoolTemplate.objects.create(school_id=self.school_id, template_id=self.template_id)
        res = get_default_template_for_school(self.school_id)
        self.assertEqual(res.template_id, self.template_id)

    def test_single_template_exists_for_another_school(self):
        """
        Data api method should raise an NoTemplateExistsForSchool exception if no template exists for school,
        even if there are templates that exist for other schools
        """
        CanvasSchoolTemplate.objects.create(school_id='another-school', template_id=self.template_id)
        with self.assertRaises(NoTemplateExistsForSchool):
            get_default_template_for_school(self.school_id)

    def test_no_default_template_exists_for_school(self):
        """ Data api method should raise an NoTemplateExistsForSchool exception if no template exists for school """
        with self.assertRaises(NoTemplateExistsForSchool):
            get_default_template_for_school(self.school_id)

    def test_multiple_default_templates_exist_for_school(self):
        """
        Data api method should raise a MultipleDefaultTemplatesExistForSchool exception
        if > 1 default templates exist for school
        """
        CanvasSchoolTemplate.objects.create(school_id=self.school_id, template_id=self.template_id)
        CanvasSchoolTemplate.objects.create(school_id=self.school_id, template_id=self.template_id + 1)

        with self.assertRaises(MultipleDefaultTemplatesExistForSchool):
            get_default_template_for_school(self.school_id)

    @patch('canvas_course_site_wizard.models_api.CanvasCourseGenerationJob.objects.get')
    def test_get_course_generation_data_for_sis_course_id_without_bulk_job_id(self, mock_ci):
        """
        Test that get_course_generation_data_for_sis_course_id has the proper query when no
        bulk job id is present
        :param mock_ci:
        :return:
        """
        get_course_generation_data_for_sis_course_id(self.sis_course_id)
        mock_ci.assert_called_once_with(sis_course_id=self.sis_course_id, bulk_job_id__isnull=True)

    @patch('canvas_course_site_wizard.models_api.CanvasCourseGenerationJob.objects.get')
    def test_get_course_generation_data_for_sis_course_id(self, mock_ci):
        """
        Test that get_course_generation_data_for_sis_course_id has the proper query when the
        bulk job id is present
        :param mock_ci:
        :return:
        """
        get_course_generation_data_for_sis_course_id(self.sis_course_id, bulk_job_id=self.bulk_job_id)
        mock_ci.assert_called_once_with(bulk_job_id=self.bulk_job_id, sis_course_id=self.sis_course_id)


    #TODO: once we figure out how to deal with legacy data, we can add integration tests for retrieving course data
