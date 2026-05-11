from pathlib import Path
from decouple import config
from datetime import timedelta
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', cast=bool, default=True)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'ninja',
    'ninja_jwt',
    'django_celery_results',
    'agents',
    'integrations',
    'conversations',
    'contacts',
    'corsheaders',
    'encrypted_model_fields',
    'channels',
    'templates',
    'labels',
    'campaigns',
    'billing',
    'automations',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'ninja.compatibility.files.fix_request_files_middleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'core.asgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB'),
        'USER': config('POSTGRES_USER'),
        'PASSWORD': config('POSTGRES_PASSWORD'),
        'HOST': config('POSTGRES_HOST', default='localhost'),
        'PORT': config('POSTGRES_PORT', default='5432'),
        'CONN_MAX_AGE': 60,
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'pt-BR'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
STATIC_URL = 'static/'

# Sentry

sentry_sdk.init(
    dsn=config('SENTRY_DSN', default=''),
    integrations=[DjangoIntegration(), CeleryIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False
)


# Storages

STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'OPTIONS': {
            'endpoint_url': config('MINIO_ENDPOINT_URL'),
            'access_key': config('MINIO_ACCESS_KEY'),
            'secret_key': config('MINIO_SECRET_KEY'),
            'bucket_name': config('MINIO_BUCKET_NAME'),
            'default_acl': 'public-read',
            'querystring_auth': False,
            'file_overwrite': False,
        }
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    }
}


# JWT

NINJA_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7)
}

# Redis

REDIS_URL = config('REDIS_URL')

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://localhost:6380/0')]
        },
    }
}

# Celery

CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_TASK_RESULT_EXPIRES = 3600
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

CELERY_TASK_ROUTES = {
    'conversations.tasks.process_message': {'queue': 'ai'},
    'conversations.tasks.transcribe_and_process_message': {'queue': 'ai'},
}

CELERY_BEAT_SCHEDULE = {
    'check-follow-ups': {
        'task': 'conversations.tasks.check_follow_ups',
        'schedule': 1800 # (seconds)
    }
}


FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@seudominio.com')

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', cast=int, default=587)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool, default=True)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')


# EvoGO - Whatsapp 

EVOGO_BASE_URL = config('EVOGO_BASE_URL')
EVOGO_GLOBAL_API_KEY = config('EVOGO_GLOBAL_API_KEY')
BASE_URL = config('BASE_URL')


APPEND_SLASH = False

# Transcription
GROQ_API_KEY = config('GROQ_API_KEY')

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS').split(',')
_csrf_raw = config('CSRF_TRUSTED_ORIGINS', default='')
CSRF_TRUSTED_ORIGINS = _csrf_raw.split(',') if _csrf_raw else CORS_ALLOWED_ORIGINS

# Proxy SSL
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Crypt
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY')

# Stripe
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET')

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
