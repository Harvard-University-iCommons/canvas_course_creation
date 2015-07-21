"""
Django settings for icommons_lti_tools project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""
import os
from os.path import abspath, basename, dirname, join, normpath
from sys import path
from .secure import SECURE_SETTINGS
from django.core.urlresolvers import reverse_lazy

# Normally you should not import ANYTHING from Django directly
# into your settings, but ImproperlyConfigured is an exception.
from django.core.exceptions import ImproperlyConfigured


def get_env_variable(var_name):
    """ Get the environment variable or return exception """
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the %s environment variable" % var_name
        raise ImproperlyConfigured(error_msg)


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = dirname(dirname(__file__))

"""
Path stuff as recommended by Two Scoops / with local mods
"""

# Absolute filesystem path to the Django project config directory:
# (this is the parent of the directory where this file resides,
# since this file is now inside a 'settings' pacakge directory)
DJANGO_PROJECT_CONFIG = dirname(dirname(abspath(__file__)))

# Absolute filesystem path to the top-level project folder:
# (this is one directory up from the project config directory)
SITE_ROOT = dirname(DJANGO_PROJECT_CONFIG)

# Site name:
SITE_NAME = basename(SITE_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(SITE_ROOT)

"""
End path stuff
"""

# THESE ADDRESSES WILL RECEIVE EMAIL ABOUT CERTAIN ERRORS!
ADMINS = SECURE_SETTINGS.get('admins')

# This is the address that emails will be sent "from"
SERVER_EMAIL = 'iCommons LTI Tools <icommons-bounces@harvard.edu>'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mailhost.harvard.edu'
EMAIL_USE_TLS = True


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SECURE_SETTINGS.get('django_secret_key', 'changeme')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = SECURE_SETTINGS.get('enable_debug', False)

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ['*']

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Database

DATABASE_APPS_MAPPING = {
    'icommons_common': 'termtool',
    'canvas_course_site_wizard': 'termtool',
    'auth': 'default',
    'contenttypes': 'default',
    'sessions': 'default',
    'student_locations': 'default',
    'lecture_video': 'termtool',
    'reserves_list': 'termtool',
    'add_people': 'termtool',
    'course_add_people': 'termtool',
}

DATABASE_MIGRATION_WHITELIST = ['default']

DATABASE_ROUTERS = ['icommons_common.routers.DatabaseAppsRouter', ]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': SECURE_SETTINGS.get('db_default_name', 'icommons_lti_tools'),
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


# Cache

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
        'KEY_PREFIX': 'icommons_lti_tools'
    },
}


# Sessions

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Django defaults to False (as of 1.7)
SESSION_COOKIE_SECURE = SECURE_SETTINGS.get('use_secure_cookies', False)


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
    'lecture_video',
    'crispy_forms',
    'reserves_list',
    'student_locations',
    'add_people',
    'course_add_people',
    'bulk_site_creation',
    'tools_usage'
)

MIDDLEWARE_CLASSES = (
    'djangular.middleware.DjangularUrlMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',

    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'cached_auth.Middleware',

    'django_auth_lti.middleware_patched.MultiLTILaunchAuthMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'django_auth_lti.backends.LTIAuthBackend',
)

CRISPY_TEMPLATE_PACK = 'bootstrap3'


LOGIN_URL = reverse_lazy('lti_auth_error')

ROOT_URLCONF = 'icommons_lti_tools.urls'

WSGI_APPLICATION = 'icommons_lti_tools.wsgi.application'


# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/lti_tools/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    normpath(join(SITE_ROOT, 'static')),
)

STATIC_ROOT = normpath(join(SITE_ROOT, 'http_static'))

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

LTI_OAUTH_CREDENTIALS = SECURE_SETTINGS.get('lti_oauth_credentials', None)

CANVAS_URL = SECURE_SETTINGS.get('canvas_url', 'https://canvas.harvard.edu')

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

ISITES_LMS_URL = ''

CANVAS_SITE_SETTINGS = {
    'base_url': CANVAS_URL + '/',
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

SECTIONS_TOOL = {
    'TEST_STUDENT_ROLE': 'StudentViewEnrollment'
}

RESERVES_CONFIG = {
    'ISITES_TOOL_URL': 'http://isites.harvard.edu/icb/icb.do?keyword=reserves&pageid=icb.page.topiceditgeneral.icb.topic1452049.icb.page.inlinecontent.icb.page686958.icb.page686958&pageContentId=icb.pagecontent1505871&view=edit&viewParam_courseInstanceId={0}',
    'RESERVES_URL': 'http://webservices.lib.harvard.edu/ecru/v2/readings/courses/',
    'RESERVES_ITEM_URL': 'http://webservices.lib.harvard.edu/ecru/v2/readings/',
}

STUDENT_LOCATIONS_TOOL = {
    'google_map_api_v3_key': SECURE_SETTINGS.get('google_map_api_v3_key'),
}

LECTURE_VIDEO_TOOL = {
    'DVS_API_HOST': 'http://tool2.isites.harvard.edu:8937',
    'JW_PLAYER_KEY': SECURE_SETTINGS.get('jwplayerkey', None),
    'CACHE_TIMEOUT': SECURE_SETTINGS.get('lecture_video_cache_timeout', 60 * 60 * 2),  # Default to 2 hours
    'API_CALL_TIMEOUT': 15,  # 15 seconds
}

TOOLS_USAGE = {
    's3_bucket': SECURE_SETTINGS.get('tools_usage_s3_bucket', ''),
    's3_key_template': 'external_tools/external_tools_{}.html',
    's3_url_expiration_secs': SECURE_SETTINGS.get(
        'tools_usage_s3_url_expiration_secs', 60
    ),
}


CAP_MSGS = {
    'lti_request': 'There was a problem fulfilling your request. Please contact HUIT support.',
    'no_dir_member_chosen': 'You must choose at least one directory record.',
    'no_role_selected': 'You must choose a role for each user you select.',
    'no_user_selected': 'You must select a user for each role you choose.',
    'success': 'Successful !!!',

}

CAP_BADGE_LABELS = {
    'huid': 'HUID',
    'xid': 'XID',
    'library': 'LIBRARY',
    'other': 'OTHER',
}

_LOG_ROOT = SECURE_SETTINGS.get('log_root', '')  # Default to current directory

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
            'filename': join(_LOG_ROOT, 'django-icommons_lti_tools.log'),
            'formatter': 'verbose',
        },
        'manage_people_audit_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': join(_LOG_ROOT, 'django-manage_people_audit.log'),
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
        'lecture_video': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'reserves_list': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'student_locations': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'add_user': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'wordpress': {
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
        'canvas_course_site_wizard': {
            'handlers': ['console', 'logfile'],
            'level': 'INFO',
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
        'add_people': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'course_add_people': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'bulk_site_creation': {
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'manage_people_audit_log': {
            'handlers': ['console', 'manage_people_audit_log_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}
