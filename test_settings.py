"""
These settings are here to use during tests, because django requires them.

In a real-world use case, apps in this project are installed into other
Django applications, so these settings will not be used.
"""

from __future__ import absolute_import, unicode_literals

from os.path import abspath, dirname, join

from unlockerx.helpers.settings_helpers import update_middlewares

DEBUG = True


def root(*args):
    """
    Get the absolute path of the given path relative to the project root.
    """
    return join(abspath(dirname(__file__)), *args)


# Calling `update_middlewares` to mock the behaviour of the Open edX plugins system.
# Ref: https://github.com/edx/edx-platform/blob/ac4845d/openedx/core/djangoapps/plugins/README.rst
# Keep in parity with `unlockerx.settings.common` to ensure proper testing environment.
MIDDLEWARE_CLASSES = update_middlewares([
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # Enable SessionAuthenticationMiddleware in order to invalidate
    # user sessions after a password change.
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',

    # catches any uncaught RateLimitExceptions and returns a 403 instead of a 500
    'ratelimitbackend.middleware.RateLimitMiddleware',
])


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'default.db',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'ATOMIC_REQUESTS': True,
    }
}

AUTHENTICATION_BACKENDS = (
    'ratelimitbackend.backends.RateLimitModelBackend',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'unlockerx',
    'student',
    'ratelimitbackend',
)

LOCALE_PATHS = [
    root('unlockerx', 'conf', 'locale'),
]

ROOT_URLCONF = 'unlockerx.urls'

SECRET_KEY = 'insecure-secret-key'

USE_TZ = True


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
