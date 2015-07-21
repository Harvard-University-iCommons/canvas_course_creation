import collections

from django.conf import settings

from icommons_ui.exceptions import RenderableException


class NoTemplateExistsForSchool(Exception):
    def __init__(self, school_id):
        self.school_id = school_id

    def __unicode__(self):
        return u'No template exists for school_id=%s' % self.school_id

    def __str__(self):
        return 'No template exists for school_id=%s' % self.school_id


class MultipleDefaultTemplatesExistForSchool(Exception):
    def __init__(self, school_id):
        self.school_id = school_id

    def __unicode__(self):
        return u'Multiple default templates exist for school_id=%s' % self.school_id

    def __str__(self):
        return 'Multiple default templates exist for school_id=%s' % self.school_id


class RenderableExceptionWithDetails(RenderableException):
    # The parameter msg_details can be used to format the message (i.e. it can be substituted into the
    # display text)
    def __init__(self, msg_details, *args, **kw_args):
        super(RenderableExceptionWithDetails, self).__init__(self, *args, **kw_args)
        if (isinstance(msg_details, collections.Iterable)
                and not isinstance(msg_details, basestring)):
            self.display_text = self.display_text.format(*msg_details)
        else:
            self.display_text = self.display_text.format(msg_details)


class NoCanvasUserToEnroll(RenderableExceptionWithDetails):
    # Do not display any additional information about the Canvas user not existing directly to the user;
    # handle this as a failure to enroll the creator. Logs will capture the exact issue.
    display_text = 'Error: Site creator not added for CID {0}'
    status_code = 404  # Canvas user not found


class CanvasEnrollmentError(RenderableExceptionWithDetails):
    display_text = 'Error: Site creator not added for CID {0}'


class CopySISEnrollmentsError(RenderableExceptionWithDetails):
    display_text = 'Error: Sync to Canvas not working for CID {0}'


class MarkOfficialError(RenderableExceptionWithDetails):
    display_text = 'Official flag or external URL not set for CID {0}'

class CourseGenerationJobCreationError(RenderableExceptionWithDetails):
    display_text = 'Error: Unable to setup Canvas Course Creation for CID {0}'

class CanvasCourseCreateError(RenderableExceptionWithDetails):
    display_text = 'Error: SIS ID not applied for CID {0}'
    #set the support_notified attribute for this exception, in order to customize the message to the user indicating that support has been notified. 
    # *** Note : if there is a need for more such gernal purpose attributes in future, we could 
    #implement this with a an Exception mixin that sets custom fields in a list or dict 
    support_notified = True

class CanvasCourseAlreadyExistsError(RenderableExceptionWithDetails):
    display_text = 'Course already exists in Canvas with SIS ID {0}'
    status_code = 400  # Course already exists; bad request


class CanvasSectionCreateError(RenderableExceptionWithDetails):
    display_text = 'Error: Primary section not created for CID {0}'
    #set the support_notified attribute for this exception, in order to customize the message to the user indicating that support has been notified. 
    # *** Note : if there is a need for more such gernal purpose attributes in future, we could 
    #implement this with a an Exception mixin that sets custom fields in a list or dict 
    support_notified = True

class CanvasSectionAlreadyExists(RenderableExceptionWithDetails):
    display_text = 'Section already exists in Canvas with SIS ID {0}'
    status_code = 400  # Section already exists; bad request


class SISCourseDoesNotExistError(RenderableExceptionWithDetails):
    display_text = 'Error: CID {0} not found'
    status_code = 404  # Course Instance not found

class CourseGenerationJobNotFoundError(RenderableExceptionWithDetails):
    display_text = 'Bulk job {0} does not have a subjob for SIS Course ID {1}'

class SaveCanvasCourseIdToCourseGenerationJobError(RenderableExceptionWithDetails):
    display_text = ('Unable to save Canvas course id {0} to course generation '
                    'job {1}')

class SaveCanvasCourseIdToCourseInstanceError(RenderableExceptionWithDetails):
    display_text = 'Unable to save Canvas course id {0} to course instance {1}'
