"""
Django settings for canvas_course_creation project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
import os
from .secure import SECURE_SETTINGS
from django.core.urlresolvers import reverse_lazy

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SECURE_SETTINGS.get('django_secret_key', 'changeme')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = SECURE_SETTINGS.get('enable_debug', False)

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ['*']

# THESE ADDRESSES WILL RECEIVE EMAIL ABOUT CERTAIN ERRORS!
ADMINS = SECURE_SETTINGS.get('admins')

# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_auth_lti',
    'icommons_common',
    'icommons_common.monitor',
    'icommons_ui',
    'canvas_course_site_wizard',
    'djangular',
    'crispy_forms',
    'bulk_site_creation',

)

MIDDLEWARE_CLASSES = (
    'djangular.middleware.DjangularUrlMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'cached_auth.Middleware',
    'django_auth_lti.middleware_patched.MultiLTILaunchAuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'icommons_common.auth.backends.PINAuthBackend',
    'django_auth_lti.backends.LTIAuthBackend',

)

CRISPY_TEMPLATE_PACK = 'bootstrap3'

LOGIN_URL = reverse_lazy('lti_auth_error')

ROOT_URLCONF = 'canvas_course_creation.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.normpath(os.path.join(BASE_DIR, 'templates'))],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'icommons_common.auth.context_processors.pin_context'
            ],
        },
    },
]

WSGI_APPLICATION = 'canvas_course_creation.wsgi.application'

# This is the address that emails will be sent "from"
SERVER_EMAIL = 'iCommons LTI Tools <icommons-bounces@harvard.edu>'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mailhost.harvard.edu'
EMAIL_USE_TLS = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Database config

DATABASE_APPS_MAPPING = {
    'icommons_common': 'termtool',
    'canvas_course_site_wizard': 'termtool',
    'bulk_site_creation' : 'default',
    'auth': 'default',
    'contenttypes': 'default',
    'sessions': 'default',
}

DATABASE_MIGRATION_WHITELIST = ['default']

DATABASE_ROUTERS = ['icommons_common.routers.DatabaseAppsRouter', ]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': SECURE_SETTINGS.get('db_default_name', 'canvas_course_creation'),
        'USER': SECURE_SETTINGS.get('db_default_user', 'postgres'),
        'PASSWORD': SECURE_SETTINGS.get('db_default_password'),
        'HOST': SECURE_SETTINGS.get('db_default_host', '127.0.0.1'),
        'PORT': SECURE_SETTINGS.get('db_default_port', 5432),  # Default postgres port
    },
    'termtool': {
        'ENGINE': 'django.db.backends.oracle',
        'NAME': SECURE_SETTINGS.get('db_termtool_name'),
        'USER': SECURE_SETTINGS.get('db_termtool_user'),
        'PASSWORD': SECURE_SETTINGS.get('db_termtool_password'),
        'HOST': SECURE_SETTINGS.get('db_termtool_host'),
        'PORT': str(SECURE_SETTINGS.get('db_termtool_port')),
        'OPTIONS': {
            'threaded': True,
        },
        'CONN_MAX_AGE': 0,
    }
}

# Cache config

REDIS_HOST = SECURE_SETTINGS.get('redis_host', '127.0.0.1')
REDIS_PORT = SECURE_SETTINGS.get('redis_port', 6379)

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': "%s:%s" % (REDIS_HOST, REDIS_PORT),
        'OPTIONS': {
            'PARSER_CLASS': 'redis.connection.HiredisParser'
        },
        'TIMEOUT': 60 * 20,  # 20 minutes
        'KEY_PREFIX': 'canvas_course_creation'
    },
}


# Sessions

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Django defaults to False (as of 1.7)
SESSION_COOKIE_SECURE = SECURE_SETTINGS.get('use_secure_cookies', False)

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/course_creation/static/'

STATIC_ROOT = os.path.normpath(os.path.join(BASE_DIR, 'http_static'))



LTI_OAUTH_CREDENTIALS = SECURE_SETTINGS.get('lti_oauth_credentials', None)

CANVAS_URL = SECURE_SETTINGS.get('canvas_url', 'https://canvas.harvard.edu')

ISITES_LMS_URL = ''

CANVAS_SITE_SETTINGS = {
    'base_url': CANVAS_URL + '/',
}

CANVAS_SDK_SETTINGS = {
    'auth_token': SECURE_SETTINGS.get('canvas_token', None),
    'base_api_url': CANVAS_URL + '/api',
    'max_retries': 3,
    'per_page': 40,
    'session_inactivity_expiration_time_secs': 50,
}

ICOMMONS_COMMON = {
    'ICOMMONS_API_HOST': SECURE_SETTINGS.get('icommons_api_host', None),
    'ICOMMONS_API_USER': SECURE_SETTINGS.get('icommons_api_user', None),
    'ICOMMONS_API_PASS': SECURE_SETTINGS.get('icommons_api_pass', None),
    'CANVAS_API_BASE_URL': CANVAS_URL + '/api/v1',
    'CANVAS_API_HEADERS': {
        'Authorization': 'Bearer ' + SECURE_SETTINGS.get('canvas_token', 'canvas_token_missing_from_config')
    },
}

CANVAS_EMAIL_NOTIFICATION = {
    'from_email_address': 'icommons-bounces@harvard.edu',
    'support_email_address': 'tlt_support@harvard.edu',
    'course_migration_success_subject': 'Course site is ready',
    'course_migration_success_body': 'Success! \nYour new Canvas course site has been created and is ready for you at:\n'+
            ' {0} \n\n Here are some resources for getting started with your site:\n http://tlt.harvard.edu/getting-started#teachingstaff',

    'course_migration_failure_subject': 'Course site not created',
    'course_migration_failure_body': 'There was a problem creating your course site in Canvas.\n'+
            'Your local academic support staff has been notified and will be in touch with you.\n\n'+
            'If you have questions please contact them at:\n'+
            ' FAS: atg@fas.harvard.edu\n'+
            ' DCE/Summer: AcademicTechnology@dce.harvard.edu\n'+
            ' (Let them know that course site creation failed for sis_course_id: {0} ',

    'support_email_subject_on_failure': 'Course site not created',
    'support_email_body_on_failure': 'There was a problem creating a course site in Canvas via the wizard.\n\n'+
            'Course site creation failed for sis_course_id: {0}\n'+
            'User: {1}\n'+
            '{2}\n'+
            'Environment: {3}\n',
    'environment' : 'Production',
}

BULK_COURSE_CREATION = {
    'log_long_running_jobs': True,
    'long_running_age_in_minutes': 30,
    'notification_email_subject': 'Sites created for {school} {term} term',
    'notification_email_body': 'Canvas course sites have been created for the '
                               '{school} {term} term.\n\n - {success_count} '
                               'course sites were created successfully.\n',
    'notification_email_body_failed_count': ' - {} course sites were not '
                                            'created.',
}


# Background task PID (lock) files
#   * If created in another directory, ensure the directory exists in runtime environment
PROCESS_ASYNC_JOBS_PID_FILE = 'process_async_jobs.pid'
FINALIZE_BULK_CREATE_JOBS_PID_FILE = 'finalize_bulk_create_jobs.pid'

_LOG_ROOT = SECURE_SETTINGS.get('log_root', '')  # Default to current directory


# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(module)s %(message)s'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
        # Log to a text file that can be rotated by logrotate
        'logfile': {
            'level': 'INFO',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(_LOG_ROOT, 'course_creation.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'request': {
            'level': 'DEBUG',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': 'request.log',
            'formatter': 'verbose',
        },

    },
    'loggers': {
        '': {
            'handlers': ['console', 'logfile'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['request'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers': ['console', 'logfile'],
            'level': 'ERROR',
            'propagate': True,
        },
        'oauth2': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'ims_lti_py': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django_auth_lti': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'icommons_common': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'bulk_site_creation': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'canvas_course_site_wizard': {
            'handlers': ['console', 'logfile'],
            'level': 'INFO',
            'propagate': True,
        },


    }
}
