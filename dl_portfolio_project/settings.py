# dl_portfolio_project/settings.py

import os
from pathlib import Path
import dj_database_url
# --- Add these lines ---
from dotenv import load_dotenv
import sys

# -----------------------
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Explicitly load .env from the project root ---
dotenv_path = BASE_DIR / '.env'

load_dotenv(dotenv_path=dotenv_path, override=True) # Use override=True for testing if needed

# SECURITY WARNING: keep the secret key used in production secret!
# Read secret key from environment variable in production
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-=your-default-development-key-here') # Replace fallback key

# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG to False unless an environment variable named 'DEBUG' is set to exactly 'True'
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Update ALLOWED_HOSTS based on environment
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1 localhost').split(' ')

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    
# Add your custom domain here if you set one up later
# CUSTOM_DOMAIN = os.environ.get('CUSTOM_DOMAIN')
# if CUSTOM_DOMAIN:
#     ALLOWED_HOSTS.append(CUSTOM_DOMAIN)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize', # For template filters like naturaltime
    'django.contrib.sitemaps', # Add this line
    'portfolio', # portfolio app
    'blog',      # blog app
    'skills',    # skills app
    'topics',    # topics app
    'recommendations', # Add the new app
    'demos',
    'accounts',
    #'markdownify',
    'markdownify.apps.MarkdownifyConfig',
    #'django_ratelimit',
    # Add whitenoise.runserver_nostatic if DEBUG is True for easier local static serving
    'whitenoise.runserver_nostatic', # Optional for development convenience
]

CSV_FILES = {
    'USER_PROFILE_CSV': 'data_import/00_user_profile.csv',
    'SKILLCATEGORIES_CSV': 'data_import/01_skill_categories.csv',
    'SKILLS_CSV': 'data_import/02_skills.csv',
    'TOPICS_CSV': 'data_import/03_topics.csv',
    'CERTIFICATES_CSV': 'data_import/04_certificates.csv',
    'PROJECTS_CSV': 'data_import/05_projects.csv',
    'BLOGPOSTS_CSV': 'data_import/06_blogposts.csv',
    'DEMOS_SUMMARY_CSV': 'data_import/07a_demos_summary.csv',
    'DEMOS_CONTENT_CSV': 'data_import/07b_demos_content.csv',
    'RECOMMENDATIONS_SUMMARY_CSV': 'data_import/08a_recommendations_summary.csv',
    'RECOMMENDATIONS_CONTENT_CSV': 'data_import/08b_recommendations_content.csv',
    'COLOPHON_ENTRIES_CSV': 'data_import/09_colophon_entries.csv',
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Add WhiteNoise middleware right after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'ratelimit.middleware.RatelimitMiddleware',
]

ROOT_URLCONF = 'dl_portfolio_project.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # 'DIRS': [],
        'DIRS': [BASE_DIR / 'templates'], # <--- UPDATE THIS LINE
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'portfolio.context_processors.user_profile_context',
                # Add the path to your recommendations context processor
                'recommendations.context_processors.recommendation_context',

            ],
        },
    },
]

# Redis: This is generally the preferred option for production and development if you can run a Redis server. It's fast, robust, and well-supported.
# Install Redis on your system 
# Install the Django Redis library: pip install django-redis
# # settings.py
# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": "redis://127.0.0.1:6379/1",  # Default Redis URI
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#         }
#     }
# }

WSGI_APPLICATION = 'dl_portfolio_project.wsgi.application'


# Database used in development
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", # Fallback for local dev if DATABASE_URL not set
        conn_max_age=600,
        # ssl_require can also be controlled by an env var
        # ssl_require=os.environ.get('DB_SSL_REQUIRE', 'True') == 'True'
    )
}


# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles' # For collectstatic in production


# Media files (User-uploaded content)
# https://docs.djangoproject.com/en/stable/howto/static-files/#serving-files-uploaded-by-a-user-during-development
MEDIA_URL = '/media/' # Base URL for serving media files
MEDIA_ROOT = BASE_DIR / 'mediafiles' # Absolute filesystem path to the directory for user uploads

# Staticfiles storage using WhiteNoise (Recommended for Render)
# For Django 4.2+

STORAGES = {
    # Configuration for default file storage (e.g., media files)
    # This explicitly uses the local filesystem.
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        # Optional: You can specify location and base_url if they differ from MEDIA_ROOT and MEDIA_URL
        # "OPTIONS": {
        #     "location": MEDIA_ROOT,
        #     "base_url": MEDIA_URL,
        # },
    },
    # Configuration for static files (handled by WhiteNoise in this setup)
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Email Configuration
# --------------------------------------------------------------------------
# Choose ONE backend.

# Option 1: Console backend (for development - prints emails to console)
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Option 2: SMTP backend (for production - e.g., Gmail, SendGrid, Mailgun, etc.)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com') # e.g., 'smtp.gmail.com' or your provider's SMTP server
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587)) # 587 for TLS, 465 for SSL, 25 for unencrypted (not recommended)
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True' # Use True for port 587
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False') == 'True' # Use True for port 465 (TLS and SSL are mutually exclusive)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'your_email@example.com') # Your email address or username
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'your_password_or_app_password') # ** STORE SECURELY - Use env var! **

# Default email address for 'from' field in emails sent by Django (e.g., error reports)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
# Email address for site admins to receive error notifications etc.
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', EMAIL_HOST_USER)
# ADMINS = [('Your Name', 'your_admin_email@example.com')] # Optional: For site error notifications

if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    # ... other production security settings ...
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') # Likely needed for Render

MARKDOWNIFY = {
    "default": {
        "STRIP": False,  # Keep HTML tags produced by Markdown conversion
        "WHITELIST_TAGS": [ # Common and useful tags
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'strong', 'em', 'a', 'span', 'div',
            'ul', 'ol', 'li', 'br',
            'img',
            'pre', 'code', 'blockquote',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'hr', 'del', 'ins', 'sup', 'sub',
            # Add other tags you explicitly trust or need
        ],
        "MARKDOWN_EXTENSIONS": [
            'markdown.extensions.fenced_code',    # For ```code``` blocks
            'markdown.extensions.codehilite',     # For syntax highlighting (requires Pygments)
            'markdown.extensions.tables',         # For tables
            'markdown.extensions.nl2br',          # For converting single newlines to <br>
            'markdown.extensions.extra',          # Includes abbreviations, attribute lists, footnotes, smartypants, etc.
            'markdown.extensions.toc',            # For Table of Contents (if you use [TOC])
            'markdown.extensions.sane_lists',     # For more predictable list behavior
            'markdown.extensions.admonition',     # For admonition blocks (note, warning, etc.)
        ],
        "CODEHILITE_CSS_CLASS": 'codehilite', # Default is 'codehilite'
        # Note: Other settings like WHITELIST_ATTRS, WHITELIST_STYLES, etc.
        # would also go in here if you were using them.
        # Check the documentation for all available options.
    }
    # You can define other profiles here if needed, e.g.:
    # "alternative": {
    #     "STRIP": True,
    #     "WHITELIST_TAGS": ['p', 'a'],
    #     ...
    # }
}
# --- End Markdownify Configuration ---

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False, # Keep Django's default loggers active
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG', # Log DEBUG and higher to console
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_app_errors': { # Handler for application error logs
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/app_errors.log', # Ensure 'logs' directory exists
            'formatter': 'verbose',
        },
        'mail_admins': { # Django's default handler for emailing admins on server errors
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
            'filters': ['require_debug_false'], # Only active if DEBUG is False
        }
    },
    'loggers': {
        'django': { # Default Django loggers
            'handlers': ['console', 'mail_admins'], # Send Django's logs to console and mail_admins
            'level': 'INFO', # Log INFO and higher from Django itself
            'propagate': False,
        },
        'django.request': { # Specifically for request handling errors
            'handlers': ['mail_admins', 'console'], # Ensure 500 errors are emailed and logged to console
            'level': 'ERROR',
            'propagate': False, # Don't pass to parent 'django' logger if handled here
        },
        # --- Your Application Loggers ---
        'portfolio': { # Logger for your 'portfolio' app
            'handlers': ['console', 'file_app_errors'], # Send portfolio logs to console and file
            'level': 'DEBUG', # Capture DEBUG and higher from your portfolio app
            'propagate': True, # Allow propagation if needed for other root handlers
        },
        'blog': { # Example for another app
            'handlers': ['console', 'file_app_errors'],
            'level': 'DEBUG',
            'propagate': True,
        },
        # Add loggers for your other apps (skills, topics, demos, recommendations) similarly
        # 'skills': { ... },
        # 'topics': { ... },
        # etc.
    },
    'root': { # Catch-all for any loggers not explicitly defined
        'handlers': ['console'],
        'level': 'WARNING', # Default level for other loggers
    },
    'filters': { # Filter to ensure mail_admins only runs when DEBUG=False
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
}

# Ensure the 'logs' directory exists if using FileHandler
LOGS_DIR = BASE_DIR / 'logs'
if not LOGS_DIR.exists():
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Warning: Could not create logs directory {LOGS_DIR}. Error: {e}")

# --- Add Login/Logout Redirect URLs ---
LOGIN_URL = 'login' # Name of the login URL pattern (default from django.contrib.auth.urls)
LOGIN_REDIRECT_URL = 'accounts:members_page'  # After login, go to members page
LOGOUT_REDIRECT_URL = 'portfolio:index'      # After logout, go to your portfolio's homepage
