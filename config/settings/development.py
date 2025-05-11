from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-dev-key-replace-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email settings for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable HTTPS requirements in development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# CSRF settings for easier development
# DANGER: Ne jamais utiliser ces paramètres en production!
CSRF_USE_SESSIONS = True  # Store CSRF token in the session instead of in a cookie
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read the CSRF cookie
CSRF_COOKIE_SAMESITE = None

# Désactivation complète de la protection CSRF en développement
# DANGER: À NE JAMAIS UTILISER EN PRODUCTION!
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = None
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000", "https://localhost:8000", "https://127.0.0.1:8000"]

# Créer une classe pour remplacer le middleware CSRF
import os
os.environ['CSRF_DISABLED'] = 'True'

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Simplified logging for development
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Static files for development
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files for development
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Site URL for development
SITE_URL = 'http://localhost:8000'