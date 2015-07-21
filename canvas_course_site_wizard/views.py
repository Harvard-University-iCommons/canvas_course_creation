import logging
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.shortcuts import redirect
from .controller import (
    create_canvas_course,
    start_course_template_copy,
    finalize_new_canvas_course,
    get_canvas_course_url
)
from .mixins import CourseSiteCreationAllowedMixin
from icommons_ui.mixins import CustomErrorPageMixin
from .exceptions import NoTemplateExistsForSchool
from .models import CanvasCourseGenerationJob
from braces.views import LoginRequiredMixin

logger = logging.getLogger(__name__)

class CanvasCourseSiteCreateView(LoginRequiredMixin, CourseSiteCreationAllowedMixin, CustomErrorPageMixin, TemplateView):
    """
    Serves up the canvas course site creation wizard on GET and creates the
    course site on POST.
    """
    template_name = "canvas_course_site_wizard/canvas_wizard.html"
    # This is currently the project-level 500 error page, which has RenderableException logic
    custom_error_template_name = "500.html"

    def post(self, request, *args, **kwargs):
        sis_course_id = self.object.pk
        sis_user_id = 'sis_user_id:%s' % request.user.username

        # we modified create_canvas_course to return two params when it's called as part of
        # the single course creation. This is so we can keep track of the job_id
        # for the newly created job record. There's a probably a better way to handle this
        # but for now, this works
        course, course_job_id = create_canvas_course(sis_course_id, request.user.username)
        try:
            course_generation_job = start_course_template_copy(self.object, course['id'],
                                                               request.user.username, course_job_id=course_job_id)
            return redirect('ccsw-status', course_generation_job.pk)
        except NoTemplateExistsForSchool:
            # If there is no template to copy, immediately finalize the new course
            # (i.e. run through remaining post-async job steps)
            course_url = finalize_new_canvas_course(course['id'], sis_course_id, sis_user_id)
            job = CanvasCourseGenerationJob.objects.get(pk=course_job_id)
            job.update_workflow_state(CanvasCourseGenerationJob.STATUS_FINALIZED)
            return redirect(course_url)


class CanvasCourseSiteStatusView(LoginRequiredMixin, DetailView):
    """ Displays status of course creation job, including progress and result of template copy and finalization """
    template_name = "canvas_course_site_wizard/status.html"
    model = CanvasCourseGenerationJob
    context_object_name = 'content_migration_job'

    def get_context_data(self, **kwargs):
        """
        get_context_data allows us to pass additional values to the view. In this case we are passing in:
        - the canvas course url for a successfully completed job (or None if it hasn't successfully completed)
        - simplified job progress status indicators for the template to display success/failure messages
        """
        context = super(CanvasCourseSiteStatusView, self).get_context_data(**kwargs)
        logger.debug('Rendering status page for course generation job %s' % self.object)
        context['canvas_course_url'] = get_canvas_course_url(canvas_course_id=self.object.canvas_course_id)
        context['job_failed'] = self.object.workflow_state in [
            CanvasCourseGenerationJob.STATUS_FAILED,
            CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
            CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED
        ]
        context['job_succeeded'] = self.object.workflow_state in [CanvasCourseGenerationJob.STATUS_FINALIZED]
        return context
