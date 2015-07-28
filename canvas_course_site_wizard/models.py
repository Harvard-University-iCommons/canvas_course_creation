import logging
import time

from datetime import datetime, timedelta
from django.db.models import Q
from icommons_common.models import CourseInstance, CourseSite, SiteMap, SiteMapType
from django.conf import settings
from django.db import models


logger = logging.getLogger(__name__)


class SISCourseDataMixin(object):
    """
    Extends an SIS-fed CourseInstance object with methods and properties needed for course site
    creation in an extenal LMS.  Designed as a mixin to make unit testing easier.
    """

    # Class constants for the sync_to_canvas column / flag used by set_sync_to_canvas()
    TURN_ON_SYNC_TO_CANVAS = 1
    TURN_OFF_SYNC_TO_CANVAS = 0

    @property
    def sis_account_id(self):
        """
        Derives an sis_account_id for this course.  Repeated calls will return the previously
        calculated value.
        :returns: formatted string
        """
        if not hasattr(self, '_sis_account_id'):
            if self.course.course_groups.count() > 0:
                self._sis_account_id = 'coursegroup:%d' % self.course.course_groups.first().pk
            elif self.course.departments.count() > 0:
                self._sis_account_id = 'dept:%d' % self.course.departments.first().pk
            else:
                self._sis_account_id = 'school:%s' % self.course.school_id
        return self._sis_account_id

    @property
    def course_code(self):
        """
        Derives the course code for this course.  Repeated calls will return the previously
        calculated value.
        :returns: string
        """
        if not hasattr(self, '_course_code'):
            if self.short_title:
                self._course_code = self.short_title
            elif self.course.registrar_code_display:
                self._course_code = self.course.registrar_code_display
            else:
                self._course_code = self.course.registrar_code
        return self._course_code

    @property
    def course_name(self):
        """
        Derives the course name for this course.  Appends the sub_title field to the name if :
        present.
        :returns: formatted string
        """
        if not hasattr(self, '_course_name'):
            cname = self.title or self.course_code
            if self.sub_title:
                cname += ': %s' % self.sub_title
            self._course_name = cname
        return self._course_name

    @property
    def sis_term_id(self):
        """
        Calculates and returns the sis_term_id for this course.  Repeated calls will return the
        previously calculated value.
        :returns: formatted string or None
        """
        if not hasattr(self, '_sis_term_id'):
            self._sis_term_id = self.term.meta_term_id()
        return self._sis_term_id

    @property
    def school_code(self):
        """
        Returns the school code for this course.
        :returns: string
        """
        return self.course.school_id

    @property
    def shopping_active(self):
        """
        Shopping status of the course; ie the course is shoppable (returns True) if it is in a term for which shopping
         is turned on and the course is not explicitly excluded from shopping.
        :returns: boolean
        """
        return self.term.shopping_active and not self.exclude_from_shopping

    def get_official_course_site_url(self):
        """
        Return the url for the official course website associated with this course.  If more than
        one course site is marked as official, returns the url for the first one.
        :return: url or None
        """
        if not hasattr(self, '_official_course_site_url'):
            official_sites = self.sites.filter(sitemap__map_type_id='official')
            if official_sites:
                # We're making the decision at this point to get the first official site provided.
                # If the site_type_id is 'isite' we need to build the url and append the keyword
                # if not, then we have a whole url for the external site so we can use it directly.
                site = official_sites[0]
                if site.site_type_id == 'isite':
                    self._official_course_site_url = getattr(settings, 'ISITES_LMS_URL', 'http://') + site.external_id
                else:
                    self._official_course_site_url = site.external_id
            else:
                self._official_course_site_url = None
        return self._official_course_site_url

    def set_official_course_site_url(self, url):
        """
        Creates the records necessary to make the given url the official course site for this course.
        Returns the newly created CourseSite object.
        """
        site = CourseSite.objects.create(site_type_id='external', external_id=url)
        sitemap_type = SiteMapType.objects.get(map_type_id='official')
        SiteMap.objects.create(course_instance=self, course_site=site, map_type=sitemap_type)
        return site

    def primary_section_name(self):
        """
        Derives the name of the primary (main) section for this course.
        :returns: formatted string
        """
        return '%s %s' % (self.course.school_id.upper(), self.course_code)

    def set_sync_to_canvas(self, sync_to_canvas_flag):
        """
        Updates the sync_to_canvas column of the course instance record. Currently the
        values being used are 0(no sync) and 1 (sync). But  there is some discussion to use more 
        values to to do partial sync(teaching staff only, students only , etc) in the future.
        Returns the updated object  - of type SISCourseDataMixin.
        """
        self.sync_to_canvas = sync_to_canvas_flag
        self.save(update_fields=['sync_to_canvas'])
        return self


class SISCourseData(CourseInstance, SISCourseDataMixin):
    """
    Database-backed SIS course information that implements mixin.
    """
    class Meta:
        app_label = 'icommons_common'
        proxy = True


class CanvasCourseGenerationJobManager(models.Manager):
    """
    Custom manager for CanvasCourseGenerationJob
    """
    def filter_complete(self, **kwargs):
        kwargs.update({
            'workflow_state__in': [
                CanvasCourseGenerationJob.STATUS_FINALIZED,
                CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED,
                CanvasCourseGenerationJob.STATUS_FAILED,
                CanvasCourseGenerationJob.STATUS_SETUP_FAILED
            ]
        })
        return self.filter(**kwargs)

    def filter_successful(self, **kwargs):
        kwargs.update({'workflow_state': CanvasCourseGenerationJob.STATUS_FINALIZED})
        return self.filter(**kwargs)

    def filter_failed(self, **kwargs):
        kwargs.update({
            'workflow_state__in': [
                CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED,
                CanvasCourseGenerationJob.STATUS_FAILED,
                CanvasCourseGenerationJob.STATUS_SETUP_FAILED
            ]
        })
        return self.filter(**kwargs)

    def filter_setup_for_bulkjobs(self, **kwargs):
        """
        filters CanvasCourseGenerationJobs with a workflow state of STATUS_SETUP
        Also checks to make sure bulk_job_id is not null, we don't want to get jobs started through the single create course.
        """
        kwargs.update({
            'workflow_state': CanvasCourseGenerationJob.STATUS_SETUP,
            'bulk_job_id__isnull': False
        })
        return self.filter(**kwargs)


class CanvasCourseGenerationJob(models.Model):
    """
    This model was originally for tracking the status of Canvas migration jobs (i.e. template copy jobs, which
     Canvas runs asynchronously). It is now used to track the whole Canvas course creation process, from the
     initial setup of a new Canvas course, to the migration (if required), to the finalization steps
     (e.g. syncing registrar feeds to Canvas, marking courses as official, etc.).
     New states: 'finalize' and 'finalize_failed' record the state of the 'finalize_new_canvas_course'
     process that occurs after content migration. 'setup' and 'setup_failed' track the status of course
     records prior to content migration.
    """
    # Workflow status values

    # TODO: consider modifying the values in the workflow_status column to prefix the  Canvas migration
    # statuses with `migration_*' to differentiate them from other states of the course generation
    # e.g. modify STATUS_FAILED = 'failed' to STATUS_MIGRATION_FAILED = 'migration_failed'

    STATUS_SETUP = 'setup'
    STATUS_SETUP_FAILED = 'setup_failed'
    STATUS_QUEUED = 'queued'
    STATUS_RUNNING = 'running'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_PENDING_FINALIZE = 'pending_finalize'
    STATUS_FINALIZED = 'finalized'
    STATUS_FINALIZE_FAILED = 'finalize_failed'

    # Workflow status choices
    WORKFLOW_STATUS_CHOICES = (
        (STATUS_SETUP, STATUS_SETUP),
        (STATUS_SETUP_FAILED, STATUS_SETUP_FAILED),
        (STATUS_QUEUED, STATUS_QUEUED),
        (STATUS_RUNNING, STATUS_RUNNING),
        (STATUS_COMPLETED, STATUS_COMPLETED),
        (STATUS_FAILED, STATUS_FAILED),
        (STATUS_PENDING_FINALIZE, STATUS_PENDING_FINALIZE),
        (STATUS_FINALIZED, STATUS_FINALIZED),
        (STATUS_FINALIZE_FAILED, STATUS_FINALIZE_FAILED),
    )

    # User friendly identifiers for states
    STATUS_DISPLAY_NAMES = {
        STATUS_SETUP: 'Queued',
        STATUS_SETUP_FAILED: 'Failed',
        STATUS_QUEUED: 'Queued',
        STATUS_RUNNING: 'Running',
        STATUS_COMPLETED: 'Running',
        STATUS_PENDING_FINALIZE: 'Running',
        STATUS_FAILED: 'Failed',
        STATUS_FINALIZED: 'Complete',
        STATUS_FINALIZE_FAILED: 'Failed'
    }

    canvas_course_id = models.IntegerField(null=True, blank=True, db_index=True)
    sis_course_id = models.CharField(max_length=20, db_index=True)
    content_migration_id = models.IntegerField(null=True, blank=True,)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    status_url = models.CharField(null=True, blank=True, max_length=200)
    workflow_state = models.CharField(max_length=20, choices=WORKFLOW_STATUS_CHOICES, default=STATUS_SETUP)
    created_by_user_id = models.CharField(max_length=20)
    bulk_job_id = models.IntegerField(null=True, blank=True)

    objects = CanvasCourseGenerationJobManager()

    class Meta:
        db_table = u'canvas_course_generation_job'

    def __unicode__(self):
        #TODO: unit test for this method (skipped to support bug fix in QA testing)
        return "(CanvasCourseGenerationJob ID=%s: sis_course_id=%s | %s)" % (self.pk, self.sis_course_id,
                                                                              self.workflow_state)

    @property
    def status_display_name(self):
        return CanvasCourseGenerationJob.STATUS_DISPLAY_NAMES[self.workflow_state]

    def update_workflow_state(self, workflow_state, raise_exception=False):
        """
        Updates job workflow_state. Return True if update succeeded. If raise_exception param is not True, or not provided,
         it will return False if update fails. If raise_exception is True, it will re-raise failures/exceptions.
        """
        self.workflow_state = workflow_state
        try:
            self.save(update_fields=['workflow_state'])
        except Exception as e:
            if raise_exception:
                raise e
            else:
                return False
        return True


class CanvasSchoolTemplate(models.Model):
    template_id = models.IntegerField()
    school_id = models.CharField(max_length=10, db_index=True)
    is_default = models.BooleanField(default=False)
    include_course_info = models.BooleanField(default=False)

    class Meta:
        db_table = u'canvas_school_template'

    def __unicode__(self):
        #TODO: unit test for this method (skipped to support bug fix in QA testing)
        return "(CanvasSchoolTemplate ID=%s: school_id=%s | template_id=%s" % (self.pk, self.school_id,
                                                                               self.template_id)


class BulkCanvasCourseCreationJobManager(models.Manager):
    """
    Custom manager for BulkCanvasCourseCreationJob
    """
    def create_bulk_job(self, **kwargs):
        school_id = kwargs.get('school_id')
        sis_term_id = kwargs.get('sis_term_id')
        sis_department_id = kwargs.get('sis_department_id')
        sis_course_group_id = kwargs.get('sis_course_group_id')
        template_canvas_course_id = kwargs.get('template_canvas_course_id')
        created_by_user_id = kwargs.get('created_by_user_id')
        course_instance_ids = kwargs.get('course_instance_ids')

        bulk_job = BulkCanvasCourseCreationJob(
            school_id=school_id,
            sis_term_id=sis_term_id,
            sis_department_id=sis_department_id,
            sis_course_group_id=sis_course_group_id,
            template_canvas_course_id=template_canvas_course_id,
            created_by_user_id=created_by_user_id
        )
        bulk_job.save()

        if not course_instance_ids:
            filters = {
                'canvas_course_id__isnull': True,
                'exclude_from_isites': 0,
                'term_id': sis_term_id,
                'course__school': school_id
            }
            if sis_department_id:
                filters['course__departments'] = sis_department_id
            elif sis_course_group_id:
                filters['course__course_groups'] = sis_course_group_id
            course_instance_ids = [
                ci_id for ci_id in CourseInstance.objects.filter(**filters).values_list(
                    'course_instance_id',
                    flat=True
                )
            ]

        course_jobs = []
        for ci_id in course_instance_ids:
            course_job = CanvasCourseGenerationJob(
                sis_course_id=ci_id,
                bulk_job_id=bulk_job.id,
                created_by_user_id=created_by_user_id
            )
            course_jobs.append(course_job)

        start = time.time()
        CanvasCourseGenerationJob.objects.bulk_create(course_jobs)
        logger.info("Created %d CanvasCourseGenerationJobs in %d", len(course_jobs), (time.time() - start) * 1000)

        bulk_job.status = BulkCanvasCourseCreationJob.STATUS_PENDING
        bulk_job.save(update_fields=['status'])

        return bulk_job

    def get_long_running_jobs(self, older_than_date=None, older_than_minutes=None, **kwargs):
        """
        Returns a list of bulk create job objects in a non-terminal state older than
         the time provided by either the older_than_date argument (expects a datetime) or
         the older_than_minutes argument (expects an integer number of minutes representing job age)
        """

        if older_than_date is not None and older_than_minutes is not None:
            raise ValueError("requires just one of older_than_date or older_than_minutes, not both")

        if older_than_minutes is not None:
            older_than_date = datetime.now() - timedelta(minutes=older_than_minutes)
        elif older_than_date is None:
            raise ValueError("requires either older_than_date or older_than_minutes")

        kwargs.update({
            'status__in': [
                BulkCanvasCourseCreationJob.STATUS_SETUP,
                BulkCanvasCourseCreationJob.STATUS_PENDING,
                BulkCanvasCourseCreationJob.STATUS_FINALIZING
            ],
            'updated_at__lte': older_than_date
        })
        return self.filter(**kwargs)

    def get_jobs_by_status(self, status, **kwargs):
        kwargs.update({
            'status': status
        })
        return self.filter(**kwargs)



class BulkCanvasCourseCreationJob(models.Model):
    """
    This model maps the DB table that stores data about the 'bulk canvas course creation job'. Each job
    may have multiple canvas courses as part of the bulk create process, which are present in
    CanvasCourseGenerationJob and referenced using that model's bulk_job_id
    """
    # status values
    STATUS_SETUP = 'setup'
    STATUS_PENDING = 'pending'
    STATUS_FINALIZING = 'finalizing'
    STATUS_NOTIFICATION_SUCCESSFUL = 'notification_successful'
    STATUS_NOTIFICATION_FAILED = 'notification_failed'

    # status choices
    STATUS_CHOICES = (
        (STATUS_SETUP, STATUS_SETUP),
        (STATUS_PENDING, STATUS_PENDING),
        (STATUS_FINALIZING, STATUS_FINALIZING),
        (STATUS_NOTIFICATION_SUCCESSFUL, STATUS_NOTIFICATION_SUCCESSFUL),
        (STATUS_NOTIFICATION_FAILED, STATUS_NOTIFICATION_FAILED),
    )

    # User friendly identifiers for states
    STATUS_DISPLAY_NAMES = {
        STATUS_SETUP: 'Queued',
        STATUS_PENDING: 'Running',
        STATUS_FINALIZING: 'Running',
        STATUS_NOTIFICATION_FAILED: 'Complete',
        STATUS_NOTIFICATION_SUCCESSFUL: 'Complete'
    }

    school_id = models.CharField(max_length=10)
    sis_term_id = models.IntegerField()
    sis_department_id = models.IntegerField(null=True, blank=True)
    sis_course_group_id = models.IntegerField(null=True, blank=True)
    template_canvas_course_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_SETUP)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by_user_id = models.CharField(max_length=20)
    updated_at = models.DateTimeField(auto_now_add=True)

    objects = BulkCanvasCourseCreationJobManager()

    class Meta:
        db_table = u'bulk_canvas_course_crtn_job'

    def __unicode__(self):
        return "(BulkJob ID=%s: sis_term_id=%s)" % (self.pk, self.sis_term_id)

    @property
    def status_display_name(self):
        return BulkCanvasCourseCreationJob.STATUS_DISPLAY_NAMES[self.status]

    def update_status(self, status, raise_exception=False):
        """
        Updates job status. Return True if update succeeded. If raise_exception param is not True, or not provided,
         it will return False if update fails. If raise_exception is True, it will re-raise failures/exceptions.
        """
        self.status = status
        try:
            self.save(update_fields=['status'])
        except Exception as e:
            if raise_exception:
                raise e
            else:
                return False
        return True

    def ready_to_finalize(self):
        """
        A bulk job is ready to finalize if it is PENDING and none of its subjobs are in an intermediate state
        (i.e. all subjobs are in a terminal state)
        """

        subjob_intermediate_states = [
            CanvasCourseGenerationJob.STATUS_QUEUED,
            CanvasCourseGenerationJob.STATUS_RUNNING,
            CanvasCourseGenerationJob.STATUS_SETUP,
            CanvasCourseGenerationJob.STATUS_COMPLETED,
            CanvasCourseGenerationJob.STATUS_PENDING_FINALIZE
        ]
        intermediate_subjob_count = CanvasCourseGenerationJob.objects.filter(
            workflow_state__in= subjob_intermediate_states,
            bulk_job_id=self.id).count()

        return self.status == BulkCanvasCourseCreationJob.STATUS_PENDING and intermediate_subjob_count == 0

    def get_failed_subjobs(self):
        """ Returns a list of subjobs in a known failed state """

        subjob_failed_states = [
            CanvasCourseGenerationJob.STATUS_SETUP_FAILED,
            CanvasCourseGenerationJob.STATUS_FAILED,
            CanvasCourseGenerationJob.STATUS_FINALIZE_FAILED
        ]
        subjobs = CanvasCourseGenerationJob.objects.filter(
            workflow_state__in=subjob_failed_states,
            bulk_job_id=self.id)

        return list(subjobs)

    def get_failed_subjobs_count(self):
        return len(self.get_failed_subjobs())

    def get_completed_subjobs(self):
        """ Returns a list of subjobs in a known finalized state """
        subjobs = CanvasCourseGenerationJob.objects.filter(
            workflow_state=CanvasCourseGenerationJob.STATUS_FINALIZED,
            bulk_job_id=self.id
        )
        return list(subjobs)

    def get_completed_subjobs_count(self):
        return len(self.get_completed_subjobs())

