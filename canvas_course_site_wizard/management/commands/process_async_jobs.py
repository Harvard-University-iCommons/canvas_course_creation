"""
Process the Content Migration jobs in the CanvasContentMigrationJob table.
    To invoke this Command type "python manage.py process_async_jobs"
"""
from django.core.management.base import NoArgsCommand
from django.conf import settings
from django.db.models import Q
from canvas_course_site_wizard.controller import (
    get_canvas_user_profile,
    send_email_helper,
    send_failure_email,
    finalize_new_canvas_course,
    update_syllabus_body
)
from canvas_course_site_wizard.models import CanvasCourseGenerationJob
from canvas_sdk import client
from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_ui.exceptions import RenderableException
import logging
import fcntl

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

logger = logging.getLogger(__name__)
tech_logger = logging.getLogger('tech_mail')


class Command(NoArgsCommand):
    """
    Process the Canvas course generation jobs in the CanvasCourseGenerationJob table.
    To invoke this Command type "python manage.py process_async_jobs"
    """
    help = "Process the Canvas course generation jobs in the CanvasCourseGenerationJob table"

    def handle_noargs(self, **options):
        """
        select all the active job in the CanvasCourseGenerationJob table and check
        the status using the canvas_sdk.progress method
        """

        # open and lock the file used for determining if another process is running
        _pid_file = getattr(settings, 'PROCESS_ASYNC_JOBS_PID_FILE', 'process_async_jobs.pid')
        _pid_file_handle = open(_pid_file, 'w')
        try:
            fcntl.lockf(_pid_file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            # another instance is running
            logger.error("another instance of the command is already running")
            return

        jobs = CanvasCourseGenerationJob.objects.filter(Q(workflow_state=CanvasCourseGenerationJob.STATUS_QUEUED) |
                                                        Q(workflow_state=CanvasCourseGenerationJob.STATUS_RUNNING) |
                                                        Q(workflow_state=CanvasCourseGenerationJob.STATUS_PENDING_FINALIZE))

        for job in jobs:
            try:
                """
                TODO - it turns out we only really need the job_id of the content migration
                no the whole url since we are using the canvas_sdk to check the value. We should
                update this in the database and the setting method. In the meantime just parse out
                the job_id from the url.
                """
                
                job_start_message = '\nProcessing course with sis_course_id %s' % (job.sis_course_id)
                logger.info(job_start_message)
                user_profile = None

                # Check if the job is flagged for migration or is running the migration
                workflow_state = job.workflow_state

                if workflow_state in (CanvasCourseGenerationJob.STATUS_QUEUED,
                                      CanvasCourseGenerationJob.STATUS_RUNNING):
                    response = client.get(SDK_CONTEXT, job.status_url)
                    progress_response = response.json()
                    workflow_state = progress_response['workflow_state']

                    if workflow_state == CanvasCourseGenerationJob.STATUS_COMPLETED:
                        logger.info('content migration complete for course with sis_course_id %s' % job.sis_course_id)
                        # Update the Job table with the completed state immediately to indicate that the template
                        # migration was successful
                        job.workflow_state = CanvasCourseGenerationJob.STATUS_COMPLETED
                        job.save(update_fields=['workflow_state'])

                if workflow_state in (CanvasCourseGenerationJob.STATUS_COMPLETED,
                                      CanvasCourseGenerationJob.STATUS_PENDING_FINALIZE):

                    logger.debug('Workflow state updated, starting finalization process...')
                    try:
                        update_syllabus_body(job)
                        canvas_course_url = finalize_new_canvas_course(
                            job.canvas_course_id,
                            job.sis_course_id,
                            'sis_user_id:%s' % job.created_by_user_id,
                            job.bulk_job_id
                        )
                    except Exception as e:
                        # Catch exceptions from finalize method to set the workflow_state to STATUS_FINALIZE_FAILED
                        # and then re raise it so that generic tasks like tech logger, email generation will continue
                        # to be handled in the larger try block

                        job.workflow_state = CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED
                        job.save(update_fields=['workflow_state'])

                        raise

                    # Update the Job table with the STATUS_FINALIZED state if finalize is successful
                    job.workflow_state = CanvasCourseGenerationJob.STATUS_FINALIZED
                    job.save(update_fields=['workflow_state'])

                    # if this is not a bulk_job then proceed with email generation to user
                    if not job.bulk_job_id:
                        # Once finalized successfully, only the initiator needs to be emailed
                        user_profile = get_canvas_user_profile(job.created_by_user_id)
                        to_address = [user_profile['primary_email']]
                        success_msg = settings.CANVAS_EMAIL_NOTIFICATION['course_migration_success_body']
                        logger.debug("notifying success via email: to_addr=%s and adding course url =%s" % (to_address, canvas_course_url))

                        # add the course url to the  message
                        complete_msg = success_msg.format(canvas_course_url)
                        send_email_helper(settings.CANVAS_EMAIL_NOTIFICATION['course_migration_success_subject'], complete_msg, to_address)

                elif workflow_state == CanvasCourseGenerationJob.STATUS_FAILED:
                    error_text = 'Content migration failed for course with sis_course_id %s (HUID:%s)' \
                                 % (job.sis_course_id, job.created_by_user_id)
                    logger.info(error_text)
                    tech_logger.error(error_text)

                    # Update the Job table with the new state
                    job.workflow_state = CanvasCourseGenerationJob.STATUS_FAILED
                    job.save(update_fields=['workflow_state'])

                    if not job.bulk_job_id:
                        # send email to notify of failure if it's not a bulk fed course
                        user_profile = get_canvas_user_profile(job.created_by_user_id)
                        send_failure_email(user_profile['primary_email'], job.sis_course_id)

                else:
                    """
                    if the workflow_state is 'queued' or 'running' the job 
                    is not complete and a failure has not occured on Canvas.
                    log that we checked
                    Note: we won't need to update the DB as we will record only the completin or failure in the job table
                    """
                    message = 'content migration state is %s for course with sis_course_id %s' % (workflow_state, job.sis_course_id)
                    logger.info(message)

            except Exception as e:
                error_text = "There was a problem in processing the job for canvas course sis_course_id %s (HUID:%s)" \
                             % (job.sis_course_id, job.created_by_user_id)
                # Note: equivalent to .error(error_text, exc_info=1) -- logs at ERROR level
                logger.exception(error_text)

                # Use the friendly display_text for the subject of the tech_logger email if it's available
                if isinstance(e, RenderableException):
                    error_text = '%s (HUID:%s)' % (e.display_text, job.created_by_user_id)
                tech_logger.exception(error_text)

                # send email if it's not a bulk created course
                if not job.bulk_job_id:
                    try:
                        # if failure happened before user profile was fetched, get the user profile
                        # to retrieve email, else reuse the user_profile info
                        if not user_profile:
                            user_profile = get_canvas_user_profile(job.created_by_user_id)

                        send_failure_email(user_profile['primary_email'], job.sis_course_id)
                    except Exception:
                        # If exception occurs while sending failure email, log it
                        error_text = "There was a problem in sending the failure notification email to initiator " \
                                     "and support staff for sis_course_id %s (HUID:%s)" \
                                     % (job.sis_course_id, job.created_by_user_id)
                        logger.exception(error_text)
                        tech_logger.exception(error_text)

        # unlock and close the file used for determining if another process is running
        try:
            fcntl.lockf(_pid_file_handle, fcntl.LOCK_UN)
            _pid_file_handle.close()
        except IOError:
            logger.error("could not release lock on pid file or close pid file properly")
