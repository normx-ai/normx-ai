from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-test-key'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['testserver']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Email settings for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable HTTPS requirements in testing
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Simplified logging for testing
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'ERROR',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'ERROR',
    },
}

# Password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable CSRF checks in testing for API testing
MIDDLEWARE = [m for m in MIDDLEWARE if 'CsrfViewMiddleware' not in m]

# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Site URL for testing
SITE_URL = 'http://testserver'