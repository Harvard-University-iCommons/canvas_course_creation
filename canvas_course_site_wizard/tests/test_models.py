from datetime import datetime
from itertools import count
from unittest import TestCase, skip
from mock import patch, Mock
from icommons_common.models import Course, CourseInstance, Term, School, TermCode
from canvas_course_site_wizard.models import (
    BulkCanvasCourseCreationJob as BulkJob,
    CanvasCourseGenerationJob as SubJob,
    SISCourseData
)
from setup_bulk_jobs import create_jobs


def _create_bulk_job(sis_term_id=1, status=BulkJob.STATUS_SETUP):
    return BulkJob.objects.create(
        sis_term_id=sis_term_id,
        status=status
    )


def _create_subjob(content_migration_id, canvas_course_id=1, sis_course_id='1',
                   workflow_state=SubJob.STATUS_SETUP, bulk_job_id=1):
    return SubJob.objects.create(
        content_migration_id=content_migration_id,
        canvas_course_id=canvas_course_id,
        sis_course_id=sis_course_id,
        workflow_state=workflow_state,
        bulk_job_id=bulk_job_id
    )


class BulkCanvasCourseCreationJobIntegrationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Fixture data:
        - one bulk create job of each status, with a subjob of each subjob status type for each bulk job
        - one extra pending bulk create job which is ready to be finalized
        """
        BulkJob.objects.all().delete()
        SubJob.objects.all().delete()
        sub_id_generator = count(1)
        for index, (status, _) in enumerate(BulkJob.STATUS_CHOICES):
            bulk_job = _create_bulk_job(index, status=status)
            for subjob_status, _ in SubJob.WORKFLOW_STATUS_CHOICES:
                _create_subjob(sub_id_generator.next(), workflow_state=subjob_status,
                               bulk_job_id=bulk_job.id)

    @classmethod
    def tearDownClass(cls):
        """ Clear fixture data """
        BulkJob.objects.all().delete()
        SubJob.objects.all().delete()

    def test_get_long_running_jobs_integration(self):
        """ get_long_running_jobs() should return jobs older than a certain threshold age """
        expecting_all_jobs = BulkJob.objects.get_long_running_jobs(older_than_minutes=0)
        expecting_no_jobs = BulkJob.objects.get_long_running_jobs(older_than_minutes=1000)
        self.assertEqual(len(expecting_no_jobs), 0)
        # Based on fixture data, expecting one job in each 'intermediate state' (non-terminal state)
        self.assertEqual(len(expecting_all_jobs), 3)

    def test_get_long_running_jobs_older_than_date(self):
        """ get_long_running_jobs() should return jobs older than a certain threshold datetime """
        expecting_no_jobs = BulkJob.objects.get_long_running_jobs(older_than_date=datetime(1900, 1, 1))
        expecting_all_jobs = BulkJob.objects.get_long_running_jobs(older_than_date=datetime.now())
        self.assertEqual(len(expecting_no_jobs), 0)
        # Based on fixture data, expecting one job in each 'intermediate state' (non-terminal state)
        self.assertEqual(len(expecting_all_jobs), 3)

    def test_get_long_running_jobs_no_arguments(self):
        """ get_long_running_jobs() should raise error if no threshold is specified """
        with self.assertRaises(ValueError):
            BulkJob.objects.get_long_running_jobs()

    def test_get_long_running_jobs_too_many_arguments(self):
        """ get_long_running_jobs() should raise error if multiple thresholds are specified """
        with self.assertRaises(ValueError):
            BulkJob.objects.get_long_running_jobs(older_than_minutes=0, older_than_date=datetime.now())

    def test_get_completed_subjobs_integration(self):
        """ get_completed_subjobs() should only show successfully terminated subjobs for the specified bulk job """
        bulk_job = BulkJob.objects.get(status=BulkJob.STATUS_FINALIZING)
        self.assertEqual(len(bulk_job.get_completed_subjobs()), 1)
        self.assertEqual(bulk_job.get_completed_subjobs_count(), 1)

    def test_get_failed_subjobs_integration(self):
        """ get_failed_subjobs() should only show unsuccessfully terminated subjobs for the specified bulk job """
        job = BulkJob.objects.get(status=BulkJob.STATUS_FINALIZING)
        self.assertEqual(len(job.get_failed_subjobs()), 3)
        self.assertEqual(job.get_failed_subjobs_count(), 3)

    def test_ready_to_finalize_integration_not_ready(self):
        """ bulk jobs not in pending state or with non-terminal subjobs should not be designated as finalizable """
        job_not_pending = BulkJob.objects.get(status=BulkJob.STATUS_SETUP)
        # should have subjobs in non-terminal states based on fixture data, so ready_to_finalize() should fail
        job_pending_but_not_ready = BulkJob.objects.get(status=BulkJob.STATUS_PENDING)
        self.assertFalse(job_not_pending.ready_to_finalize())
        self.assertFalse(job_pending_but_not_ready.ready_to_finalize())

    def test_ready_to_finalize_integration_ready(self):
        """ a bulk job in pending state with terminal subjobs should be designated as finalizable """
        # explicitly set up a pending bulk job for which all subjobs are in a terminal state
        job_pending_and_ready = _create_bulk_job(999, status=BulkJob.STATUS_PENDING)
        subjob_finalized = _create_subjob(9999, workflow_state=SubJob.STATUS_FINALIZED, bulk_job_id=999)
        subjob_finalize_failed = _create_subjob(9999, workflow_state=SubJob.STATUS_FINALIZE_FAILED, bulk_job_id=999)
        subjob_setup_failed = _create_subjob(9999, workflow_state=SubJob.STATUS_SETUP_FAILED, bulk_job_id=999)
        self.assertTrue(job_pending_and_ready.ready_to_finalize())
        # clean up
        job_pending_and_ready.delete()
        subjob_finalized.delete()
        subjob_finalize_failed.delete()
        subjob_setup_failed.delete()


class BulkCanvasCourseCreationJobTests(TestCase):
    @patch('canvas_course_site_wizard.models.BulkCanvasCourseCreationJob.save')
    def test_update_status_success(self, m_save):
        """ If no exception is raised in the save() call then the function should return True (indicating success) """
        job = BulkJob()
        result = job.update_status(BulkJob.STATUS_SETUP)
        self.assertTrue(m_save.called)
        self.assertTrue(result)

    @patch('canvas_course_site_wizard.models.BulkCanvasCourseCreationJob.save')
    def test_update_status_fail_raise(self, m_save):
        """ If raise_exception is True, an exception in the save() call should bubble up """
        result = None
        job = BulkJob()
        m_save.side_effect = Exception
        with self.assertRaises(Exception):
            result = job.update_status(BulkJob.STATUS_SETUP, raise_exception=True)
        self.assertTrue(m_save.called)
        self.assertIsNone(result)

    @patch('canvas_course_site_wizard.models.BulkCanvasCourseCreationJob.save')
    def test_update_status_fail_gracefully(self, m_save):
        """
        If raise_exception is not provided, or is False, an exception in the save() call should not bubble up,
         and the function should return False (indicating failure)
        """
        job = BulkJob()
        m_save.side_effect = Exception
        result = job.update_status(BulkJob.STATUS_SETUP)
        self.assertTrue(m_save.called)
        self.assertFalse(result)

class SISCourseDataIntegrationTests(TestCase):

    school = None
    term_code_active = None
    term_code_inactive = None
    term_shopping_active = None
    term_shopping_inactive = None

    @classmethod
    def setUpClass(cls):
        cls.school = School.objects.create(school_id='siscdi_int')
        cls.term_code_active = TermCode.objects.create(term_code=1)
        cls.term_code_inactive = TermCode.objects.create(term_code=2)
        term_shopping_active_specs = {
            'term_id': 1,
            'term_code': cls.term_code_active,
            'shopping_active': True
        }
        term_shopping_inactive_specs = {
            'term_id': 2,
            'term_code': cls.term_code_inactive,
            'shopping_active': False
        }
        term_specs_common = {
            'academic_year': 2015,
            'calendar_year': 2015,
            'school': cls.school,
            'active': True,
            'xreg_available': True,
            'include_in_catalog': True,
            'include_in_preview': True,
        }
        term_shopping_active_specs.update(term_specs_common)
        term_shopping_inactive_specs.update(term_specs_common)
        cls.term_shopping_active = Term.objects.create(**term_shopping_active_specs)
        cls.term_shopping_inactive = Term.objects.create(**term_shopping_inactive_specs)

    @classmethod
    def tearDownClass(cls):
        cls.school.delete()
        cls.term_code_active.delete()
        cls.term_code_inactive.delete()
        cls.term_shopping_active.delete()
        cls.term_shopping_inactive.delete()

    def test_shopping_active(self):
        """
        Shopping is active for the course if course's term is shoppable
        and the course is not excluded
        """
        sis_course_data = SISCourseData(
            term=self.term_shopping_active,
            exclude_from_shopping=False
        )
        self.assertTrue(sis_course_data.shopping_active)

    def test_shopping_inactive_when_excluded(self):
        """ shopping is inactive for the course if course's term is shoppable but the course is excluded """
        sis_course_data = SISCourseData(
            term=self.term_shopping_active,
            exclude_from_shopping=True
        )
        self.assertFalse(sis_course_data.shopping_active)

    def test_shopping_inactive_when_term_inactive(self):
        """ shopping is inactive for the course if course's term is not shoppable, even if course is not excluded """
        sis_course_data = SISCourseData(
            term=self.term_shopping_inactive,
            exclude_from_shopping=False
        )
        self.assertFalse(sis_course_data.shopping_active)


class CanvasCourseGenerationJobTests(TestCase):

    def setUp(self):
        self.school_id = 'colgsas'
        self.term_id = 4848
        create_jobs(self.school_id, self.term_id)

    def test_status_display_name_setup(self):
        job = [j for j in SubJob.objects.filter(workflow_state=SubJob.STATUS_SETUP)][0]
        self.assertEqual(job.status_display_name, 'Queued')

    def test_status_display_name_setup_failed(self):
        job = [j for j in SubJob.objects.filter(workflow_state=SubJob.STATUS_SETUP_FAILED)][0]
        self.assertEqual(job.status_display_name, 'Failed')

    def test_status_display_name_queued(self):
        job = [j for j in SubJob.objects.filter(workflow_state=SubJob.STATUS_QUEUED)][0]
        self.assertEqual(job.status_display_name, 'Queued')

    def test_status_display_name_running(self):
        job = [j for j in SubJob.objects.filter(workflow_state=SubJob.STATUS_RUNNING)][0]
        self.assertEqual(job.status_display_name, 'Running')

    def test_status_display_name_completed(self):
        job = [j for j in SubJob.objects.filter(workflow_state=SubJob.STATUS_COMPLETED)][0]
        self.assertEqual(job.status_display_name, 'Running')

    def test_status_display_name_failed(self):
        job = [j for j in SubJob.objects.filter(workflow_state=SubJob.STATUS_FAILED)][0]
        self.assertEqual(job.status_display_name, 'Failed')

    def test_status_display_name_finalized(self):
        job = [j for j in SubJob.objects.filter(workflow_state=SubJob.STATUS_FINALIZED)][0]
        self.assertEqual(job.status_display_name, 'Complete')

    def test_status_display_name_finalize_failed(self):
        job = [j for j in SubJob.objects.filter(workflow_state=SubJob.STATUS_FINALIZE_FAILED)][0]
        self.assertEqual(job.status_display_name, 'Failed')

    def test_filter_complete(self):
        bulk_job = [j for j in BulkJob.objects.filter(status=BulkJob.STATUS_NOTIFICATION_SUCCESSFUL)][0]
        self.assertEqual(SubJob.objects.filter_complete(bulk_job_id=bulk_job.id).count(), 4)

    def test_filter_successful(self):
        bulk_job = [j for j in BulkJob.objects.filter(status=BulkJob.STATUS_NOTIFICATION_SUCCESSFUL)][0]
        self.assertEqual(SubJob.objects.filter_successful(bulk_job_id=bulk_job.id).count(), 1)

    def test_filter_successful(self):
        bulk_job = [j for j in BulkJob.objects.filter(status=BulkJob.STATUS_NOTIFICATION_SUCCESSFUL)][0]
        self.assertEqual(SubJob.objects.filter_failed(bulk_job_id=bulk_job.id).count(), 3)


class BulkCanvasCourseCreationJobTests(TestCase):

    def setUp(self):
        self.school_id = 'colgsas'
        self.term_id = 4848
        create_jobs(self.school_id, self.term_id)

    def test_status_display_name_setup(self):
        job = [j for j in BulkJob.objects.filter(status=BulkJob.STATUS_SETUP)][0]
        self.assertEqual(job.status_display_name, 'Queued')

    def test_status_display_name_pending(self):
        job = [j for j in BulkJob.objects.filter(status=BulkJob.STATUS_PENDING)][0]
        self.assertEqual(job.status_display_name, 'Running')

    def test_status_display_name_finalizing(self):
        job = [j for j in BulkJob.objects.filter(status=BulkJob.STATUS_FINALIZING)][0]
        self.assertEqual(job.status_display_name, 'Running')

    def test_status_display_name_notification_failed(self):
        job = [j for j in BulkJob.objects.filter(status=BulkJob.STATUS_NOTIFICATION_FAILED)][0]
        self.assertEqual(job.status_display_name, 'Complete')

    def test_status_display_name_notification_successful(self):
        job = [j for j in BulkJob.objects.filter(status=BulkJob.STATUS_NOTIFICATION_SUCCESSFUL)][0]
        self.assertEqual(job.status_display_name, 'Complete')

    @patch('icommons_common.models.CourseInstance.objects.filter')
    def test_create_bulk_job_for_filter(self, ci_filter_mock):
        school_id = 'colgsas'
        sis_term_id = 1111
        sis_department_id = 1111
        created_by_user_id = '10564158'
        course_instance_ids = [1, 2, 3]
        ci_filter_mock.return_value = [
            CourseInstance(course_instance_id=1),
            CourseInstance(course_instance_id=2),
            CourseInstance(course_instance_id=3)
        ]

        bulk_job = BulkJob.objects.create_bulk_job(
            school_id=school_id,
            sis_term_id=sis_term_id,
            sis_department_id=sis_department_id,
            created_by_user_id=created_by_user_id
        )
        ci_filter_mock.assert_called_with(
            term_id=sis_term_id,
            course__school=school_id,
            course__departments=sis_department_id
        )
        self.assertEqual(bulk_job.status, BulkJob.STATUS_PENDING)
        self.assertEqual(bulk_job.school_id, school_id)
        self.assertEqual(bulk_job.sis_term_id, sis_term_id)
        self.assertEqual(bulk_job.sis_department_id, sis_department_id)
        self.assertIsNone(bulk_job.sis_course_group_id)
        self.assertEqual(bulk_job.created_by_user_id, created_by_user_id)

        query_set_course_job = SubJob.objects.filter(bulk_job_id=bulk_job.id)
        self.assertEqual(query_set_course_job.count(), 3)
        for course_job in query_set_course_job:
            self.assertIn(int(course_job.sis_course_id), course_instance_ids)
            self.assertEqual(course_job.bulk_job_id, bulk_job.id)
            self.assertEqual(course_job.created_by_user_id, created_by_user_id)
            self.assertEqual(course_job.workflow_state, SubJob.STATUS_SETUP)

    def test_create_bulk_job_for_course_instance_ids(self):
        school_id = 'colgsas'
        sis_term_id = 1111
        sis_department_id = 1111
        created_by_user_id = '10564158'
        course_instance_ids = [1, 2, 3]

        bulk_job = BulkJob.objects.create_bulk_job(
            school_id=school_id,
            sis_term_id=sis_term_id,
            sis_department_id=sis_department_id,
            created_by_user_id=created_by_user_id,
            course_instance_ids=course_instance_ids
        )
        self.assertEqual(bulk_job.status, BulkJob.STATUS_PENDING)
        self.assertEqual(bulk_job.school_id, school_id)
        self.assertEqual(bulk_job.sis_term_id, sis_term_id)
        self.assertEqual(bulk_job.sis_department_id, sis_department_id)
        self.assertIsNone(bulk_job.sis_course_group_id)
        self.assertEqual(bulk_job.created_by_user_id, created_by_user_id)

        query_set_course_job = SubJob.objects.filter(bulk_job_id=bulk_job.id)
        self.assertEqual(query_set_course_job.count(), 3)
        for course_job in query_set_course_job:
            self.assertIn(int(course_job.sis_course_id), course_instance_ids)
            self.assertEqual(course_job.bulk_job_id, bulk_job.id)
            self.assertEqual(course_job.created_by_user_id, created_by_user_id)
            self.assertEqual(course_job.workflow_state, SubJob.STATUS_SETUP)
