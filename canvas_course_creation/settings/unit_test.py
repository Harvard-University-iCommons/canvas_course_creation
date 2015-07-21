from .local import *


DATABASE_APPS_MAPPING = {
    'icommons_common': 'default',
    'canvas_course_site_wizard': 'default',
    'auth': 'default',
    'contenttypes': 'default',
    'sessions': 'default',
    'student_locations': 'default',
    'lecture_video': 'default',
    'reserves_list': 'default',
    'add_people': 'default',
    'course_add_people': 'default',
}

DATABASE_MIGRATION_WHITELIST = ['default']

# Make tests faster by using sqlite3
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'test.db'),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

"""
Unit tests should be able to run without talking to external services like
redis/elasticache.  Let's disable the caching middleware, and use the db
to store session data.
"""
MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES)
MIDDLEWARE_CLASSES[MIDDLEWARE_CLASSES.index('cached_auth.Middleware')] = \
    'django.contrib.auth.middleware.AuthenticationMiddleware'
MIDDLEWARE_CLASSES = tuple(MIDDLEWARE_CLASSES)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

"""
Don't assume we'll have oauth credentials set for us in secure.py, set
them up here instead.
"""
SECURE_SETTINGS.setdefault('lti_oauth_credentials', {}).update({'foo': 'bar'})
if not LTI_OAUTH_CREDENTIALS:
    LTI_OAUTH_CREDENTIALS = {}
LTI_OAUTH_CREDENTIALS.update({'foo': 'bar'})
SECURE_SETTINGS.setdefault('canvas_token', 'foo')
if not CANVAS_SDK_SETTINGS:
    CANVAS_SDK_SETTINGS = {}
CANVAS_SDK_SETTINGS.update({'auth_token': 'foo'})

CANVAS_EMAIL_NOTIFICATION = {
    'from_email_address': 'icommons-bounces@harvard.edu',
    'support_email_address': 'tlt_support@harvard.edu',
    'course_migration_success_subject': 'Course site is ready',
    'course_migration_success_body': '',
    'course_migration_failure_subject': 'Course site not created',
    'course_migration_failure_body': '',
    'support_email_subject_on_failure': 'Course site not created',
    'support_email_body_on_failure': '',
    'environment': 'Production',
}
