import datetime

from canvas_course_site_wizard.models import BulkCanvasCourseCreationJob, CanvasCourseGenerationJob


def create_jobs(school_id, sis_term_id, sis_department_id=None, sis_course_group_id=None):
    """
    Create one BulkCanvasCourseCreationJob for each status
    Create one CanvasCourseGenerationJob for each status for each BulkCanvasCourseCreationJob created
    """
    for (status, _) in BulkCanvasCourseCreationJob.STATUS_CHOICES:
        bulk_job = BulkCanvasCourseCreationJob.objects.create(
            school_id=school_id,
            sis_term_id=sis_term_id,
            sis_department_id=sis_department_id,
            sis_course_group_id=sis_course_group_id,
            status=status,
            created_by_user_id="10564158"
        )
        for (workflow_state, _) in CanvasCourseGenerationJob.WORKFLOW_STATUS_CHOICES:
            CanvasCourseGenerationJob.objects.create(
                sis_course_id=1111,
                workflow_state=workflow_state,
                created_by_user_id="10564158",
                bulk_job_id=bulk_job.id
            )
