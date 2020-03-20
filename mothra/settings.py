import os
import environ
from packages.packages import PACKAGE_TREE
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

env = environ.Env()

PROJECT_DIR = os.path.dirname(__file__)
PUBLIC_DIR = os.path.join(PROJECT_DIR, 'public')
BACKUP_DIR = os.path.join(PROJECT_DIR, 'backup')

DEBUG = env.bool("DEBUG", True)

# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY", default="q8e7qoq2OWN@*W@@OW*Y&H@KSUYQG@&#^T!I@(*WUJSIQ&YWG@BYU!^FGVS2")

ADMINS = (
    # ('Anze', 'anze.vavpetic@ijs.si'),
    # ('Janez', 'janez.kranjc@ijs.si'),
    # ('Matic', 'matic.perovsek@ijs.si')
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PUBLIC_DIR, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PUBLIC_DIR, 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_DIR, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

MIDDLEWARE_CLASSES = (
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'workflows.middleware.DisableClientSideCachingMiddleware',
)

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 10
CACHE_MIDDLEWARE_KEY_PREFIX = 'mothra'

ROOT_URLCONF = 'mothra.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'mothra.wsgi.application'

FIXTURE_DIRS = (
    os.path.join(PROJECT_DIR, 'fixtures'),
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        # 'console': {
        #     'level': 'DEBUG',
        #     'class': 'logging.StreamHandler',
        # },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        # 'django.db.backends': {
        #    'level': 'DEBUG',
        # 'handlers': ['console'],
        # }
    }
}

INSTALLED_APPS_DEFAULT = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django_extensions',
    'django.contrib.humanize',
    # 'orderable_inlines',
    'workflows',
    'picklefield',
    'streams',
    'djcelery',
    'kombu.transport.django',
    'discover_runner',
    'rest_framework',
    'rest_framework.authtoken',
    'djoser',
    'rest_framework_docs',
    'corsheaders',
    'channels'
)

DJOSER = {
    'PASSWORD_RESET_CONFIRM_URL': 'password-reset/{uid}/{token}',
    'PASSWORD_RESET_CONFIRM_RETYPE': False,
    'SERIALIZERS': {},
}

USE_WINDOWS_QUEUE = False

import djcelery

djcelery.setup_loader()

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.BasicAuthentication',
    ),
    'PAGINATE_BY': None,
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',),
    'TEST_REQUEST_DEFAULT_FORMAT': 'json'
}

CORS_ORIGIN_ALLOW_ALL = True
CORS_URLS_REGEX = r'^/api/.*$'

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'pragma',
    'cache-control'
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

PROJECT_FOLDER = PROJECT_DIR

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': (os.path.join(PROJECT_DIR, 'templates'),),
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'workflows.context_processor.base_workflows_url'
            ),
            'debug': False,
            'loaders': (
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ),
        },
    },
]

AUTH_PROFILE_MODULE = 'workflows.UserProfile'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

STATIC_DOC_ROOT = os.path.join(os.getcwd(), 'mothra/public/media')

CELERY_RESULT_BACKEND = 'amqp'
CELERY_TASK_RESULT_EXPIRES = 18000
CELERY_TIMEZONE = 'UTC'

REDIS_LAYER = env.bool("REDIS_LAYER", False)

if REDIS_LAYER:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "asgi_redis.RedisChannelLayer",
            "CONFIG": {
                "hosts": [(env("REDIS_HOST", default="localhost"), env("REDIS_PORT", default=6379))],
            },
            "ROUTING": "mothra.routing.channel_routing",
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "asgiref.inmemory.ChannelLayer",
            "ROUTING": "mothra.routing.channel_routing",
        },
    }

DATABASES = {"default": env.db("DATABASE_URL", default="sqlite:///mothra.db")}

USE_CONCURRENCY = False

FILES_FOLDER = os.path.join(PUBLIC_DIR, 'files/')

INSTALLED_APPS_WORKFLOWS_SUB = (
    'workflows.base',
)

INSTALLED_APPS_EXTERNAL_PACKAGES = tuple([p for packages in PACKAGE_TREE for p in packages['packages']])

BROKER_URL = 'django://'

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

USE_WINDOWS_QUEUE = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])

if DEBUG:
    INTERNAL_IPS = type(str('c'), (), {'__contains__': lambda *a: True})()

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SENTRY_DSN = env("SENTRY_DSN", default="")

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        send_default_pii=True
    )

INSTALLED_APPS = \
    INSTALLED_APPS_DEFAULT + \
    INSTALLED_APPS_WORKFLOWS_SUB + \
    INSTALLED_APPS_EXTERNAL_PACKAGES
