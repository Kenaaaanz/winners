import os
from pathlib import Path
from decouple import config
import logging

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Create logs directory if it doesn't exist
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_extensions',
    'django_cleanup',
    #'import_export',
    'django_filters',
    'widget_tweaks',
    
    # Local apps
    'core',
    'pos',
    'inventory',
    'analytics',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.permissions.RoleRequiredMiddleware',  # Role-based access control
]

ROOT_URLCONF = 'winners.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'winners.wsgi.application'

# Database
# Using SQLite by default for easier setup
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': config('DB_NAME', default=BASE_DIR / 'db.sqlite3'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/Logout URLs
LOGIN_REDIRECT_URL = 'dashboard'
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'login'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Email Configuration (Optional - can use console backend)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'winners.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'error.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'core': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'pos': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Custom context processor
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# M-Pesa Configuration
MPESA_ENVIRONMENT = config('MPESA_ENVIRONMENT', default='sandbox')  # 'sandbox' or 'production'

# Sandbox Credentials (for testing)
MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY', default='nOcuZAiz50VIwfOQVra2xGil4W2Y1cOyBAlWzpPImZMXSUtF')
MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET', default='cZIsoViWizjimu2485UyW68YF5oU988CnsBvGQtO6EH3KoRGcpRdFsVzOj2StT4z')
MPESA_SHORTCODE = config('MPESA_SHORTCODE', default='174379')  # Sandbox: 174379
MPESA_PASSKEY = config('MPESA_PASSKEY', default='bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')

# Production Credentials (update for production)
# MPESA_CONSUMER_KEY = config('MPESA_CONSUMER_KEY_PROD', default='')
# MPESA_CONSUMER_SECRET = config('MPESA_CONSUMER_SECRET_PROD', default='')
# MPESA_SHORTCODE = config('MPESA_SHORTCODE_PROD', default='')
# MPESA_PASSKEY = config('MPESA_PASSKEY_PROD', default='')

# Initiator Credentials (for B2C, Reversal, etc.)
MPESA_INITIATOR_NAME = config('MPESA_INITIATOR_NAME', default='winners')
MPESA_INITIATOR_PASSWORD = config('MPESA_INITIATOR_PASSWORD', default='Onsare@674472')
MPESA_CERTIFICATE_PATH = config('MPESA_CERTIFICATE_PATH', default='')

# Callback URLs (will be auto-generated)
BASE_URL = config('BASE_URL', default='http://localhost:8000')

# Transaction Settings
MPESA_MAX_AMOUNT = 150000  # Maximum amount per transaction
MPESA_MIN_AMOUNT = 1       # Minimum amount per transaction
MPESA_TRANSACTION_FEE_PERCENTAGE = 0.01  # 1% transaction fee estimate

# Security
MPESA_CALLBACK_SECRET = config('MPESA_CALLBACK_SECRET', default='your-secret-key-here')