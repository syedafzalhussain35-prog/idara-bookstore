"""
Django settings for idara_project
"""

from pathlib import Path
from decimal import Decimal
import os
import dj_database_url
import cloudinary

# ==================================================
# BASE DIRECTORY
# ==================================================
BASE_DIR = Path(__file__).resolve().parent.parent


# ==================================================
# SECURITY
# ==================================================
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret")

# Security-first default for production safety.
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
if not DEBUG and SECRET_KEY == "dev-only-secret":
    raise RuntimeError("Set DJANGO_SECRET_KEY when DEBUG=False.")

allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '')
if allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = [
        '127.0.0.1',
        'localhost',
        'syedafzalhussain35.pythonanywhere.com',
    ]

render_external_host = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if render_external_host:
    if render_external_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(render_external_host)

# Ensure custom domains are always allowed, even when ALLOWED_HOSTS env is set
for host in [
    'idarakitabulshifa.com',
    'www.idarakitabulshifa.com',
    'idara-bookstore.onrender.com',
]:
    if host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(host)

# Trust Render HTTPS proxy headers and prevent CSRF issues in production
if not DEBUG:
    render_external_host = os.getenv('RENDER_EXTERNAL_HOSTNAME')
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    CSRF_TRUSTED_ORIGINS = [
        'https://idarakitabulshifa.com',
        'https://www.idarakitabulshifa.com',
    ]
    if render_external_host:
        CSRF_TRUSTED_ORIGINS.append(f"https://{render_external_host}")
    else:
        CSRF_TRUSTED_ORIGINS.append('https://idara-bookstore.onrender.com')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
# ==================================================
# APPLICATIONS
# ==================================================
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # 🔐 Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # 🌐 Providers
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',

    # ☁️ Cloudinary
    'cloudinary',
    'cloudinary_storage',

    # 🛒 App
    'store.apps.StoreConfig',
]


# ==================================================
# MIDDLEWARE
# ==================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # ✅ REQUIRED FOR ALLAUTH
    'allauth.account.middleware.AccountMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ==================================================
# URL & WSGI
# ==================================================
ROOT_URLCONF = 'idara_project.urls'
WSGI_APPLICATION = 'idara_project.wsgi.application'


# ==================================================
# TEMPLATES
# ==================================================
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
                'django.template.context_processors.media',
                'store.context_processors.navbar_categories', # ✅ Corrected position
            ],
        },
    },
]

# ==================================================
# DATABASE
# ==================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

database_url = os.getenv('DATABASE_URL')
if database_url:
    DATABASES['default'] = dj_database_url.config(
        default=database_url,
        conn_max_age=600,
        ssl_require=True,
    )


# ==================================================
# PASSWORD VALIDATION
# ==================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ==================================================
# AUTHENTICATION BACKENDS
# ==================================================
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# ==================================================
# DJANGO-ALLAUTH (UPDATED FOR DJANGO 6.0)
# ==================================================
SITE_ID = 1

# 1. Login Method
ACCOUNT_LOGIN_METHODS = {"email", "username"}

# 2. THE FIX: Define the signup form fields explicitly.
# The '*' means the field is required.
# Since 'username' is NOT in this list, it acts like "ACCOUNT_USERNAME_REQUIRED = False"
# Since 'email*' IS in this list, it acts like "ACCOUNT_EMAIL_REQUIRED = True"
ACCOUNT_SIGNUP_FIELDS = [
    "email*",       # Required email
    "password1*",   # Required password
    "password2*",   # Required password confirmation
]

# 3. Email Verification
ACCOUNT_EMAIL_VERIFICATION = "none"

# 4. Redirects
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_ON_GET = False

# ==================================================
# SOCIAL ACCOUNT SETTINGS
# ==================================================
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_LOGIN_ON_GET = False

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    },
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'FIELDS': ['id', 'email', 'name', 'first_name', 'last_name'],
        'EXCHANGE_TOKEN': True,
        'VERSION': 'v13.0',
    }
}
# ==================================================
# INTERNATIONALIZATION
# ==================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ==================================================
# STATIC FILES
# ==================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]


# ==================================================
# MEDIA FILES
# ==================================================
if DEBUG:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

# Django 4.2+ storage setting (preferred)
if DEBUG and not os.getenv('CLOUDINARY_URL'):
    # Local dev: use filesystem storage if Cloudinary isn't configured
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
        },
    }

# Allow serving static files from finders if collectstatic didn't run
WHITENOISE_USE_FINDERS = True

# ==================================================
# CACHE
# ==================================================
REDIS_URL = os.getenv("REDIS_URL", "")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "idara-cache",
        }
    }

HOME_CACHE_TTL = int(os.getenv("HOME_CACHE_TTL", "180"))
CATEGORY_CACHE_TTL = int(os.getenv("CATEGORY_CACHE_TTL", "180"))

# ==================================================
# CHECKOUT PRICING
# ==================================================
GST_RATE = Decimal(os.getenv("GST_RATE", "0"))
SHIPPING_FLAT = Decimal(os.getenv("SHIPPING_FLAT", "0"))
SHIPPING_PER_KG = Decimal(os.getenv("SHIPPING_PER_KG", "0"))

# ==================================================
# RAZORPAY
# ==================================================
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_ENABLED = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)

# ==================================================
# BOOK WATERMARK
# ==================================================
BOOK_WATERMARK_ENABLED = os.getenv("BOOK_WATERMARK_ENABLED", "true").lower() == "true"
BOOK_WATERMARK_TEXT = os.getenv("BOOK_WATERMARK_TEXT", "Idara")

# ==================================================
# AUTO FLAGS
# ==================================================
BESTSELLER_MIN_SALES = int(os.getenv("BESTSELLER_MIN_SALES", "15"))
TRENDING_DAYS = int(os.getenv("TRENDING_DAYS", "7"))

# ==================================================
# BACKGROUND TASKS
# ==================================================
ASYNC_TASKS_ENABLED = os.getenv("ASYNC_TASKS_ENABLED", "false").lower() == "true"

# ==================================================
# DEFAULT PRIMARY KEY
# ==================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==================================================
# LOGGING (capture errors in Render logs)
# ==================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}


# ==================================================
# EMAIL CONFIGURATION
# ==================================================
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 10

EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or 'no-reply@localhost'

# Publish With Us recipients (comma-separated)
PUBLISH_WITH_US_RECIPIENTS = os.getenv(
    "PUBLISH_WITH_US_RECIPIENTS",
    "publishing@cbspd.com,publicity@cbspd.com",
)

# Order alert recipients (comma-separated)
ORDER_ALERT_RECIPIENTS = os.getenv(
    "ORDER_ALERT_RECIPIENTS",
    "",
)

# ==================================================
# SENDGRID (HTTP API)
# ==================================================
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', DEFAULT_FROM_EMAIL)
SENDGRID_FROM_NAME = os.getenv('SENDGRID_FROM_NAME', 'Idara Kitab Ul Shifa')

# ==================================================
# BREVO (HTTP API)
# ==================================================
BREVO_API_KEY = os.getenv('BREVO_API_KEY')
BREVO_FROM_EMAIL = os.getenv('BREVO_FROM_EMAIL', DEFAULT_FROM_EMAIL)
BREVO_FROM_NAME = os.getenv('BREVO_FROM_NAME', 'Idara Kitab Ul Shifa')

# Use SMTP only when both values are present; otherwise print to console
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
