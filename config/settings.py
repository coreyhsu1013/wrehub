from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# =============================================================================
# Base
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _split_csv_env(key: str, default: str = "") -> list[str]:
    raw = os.getenv(key, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


# =============================================================================
# Core
# =============================================================================
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret")

DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"

# ALLOWED_HOSTS 由 .env 控制（支援 DDNS / 動態 IP）
ALLOWED_HOSTS = _split_csv_env("ALLOWED_HOSTS", "*")
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ["*"]


# =============================================================================
# Application
# =============================================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "hub.apps.HubConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # session 必須在 csrf 前
    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# =============================================================================
# Database
# =============================================================================
database_url = os.getenv("DATABASE_URL")
if database_url:
    DATABASES = {
        "default": dj_database_url.parse(database_url, conn_max_age=600)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT"),
        }
    }


# =============================================================================
# Password validation
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# =============================================================================
# I18N
# =============================================================================
LANGUAGE_CODE = "zh-hant"
TIME_ZONE = "Asia/Taipei"
USE_I18N = True
USE_TZ = True


# =============================================================================
# 🔴 Subpath mount（/wrehub，不能少）
# =============================================================================
FORCE_SCRIPT_NAME = "/wrehub"


# =============================================================================
# 🔴 Reverse Proxy / HTTPS（403 的真正關鍵）
# =============================================================================
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# =============================================================================
# Sessions / CSRF（HTTPS + subpath + Admin 登入必備）
# =============================================================================
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

SESSION_COOKIE_PATH = "/wrehub/"
CSRF_COOKIE_PATH = "/wrehub/"

# 🔴 關鍵：沒有這兩行，Admin POST 一定 403
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"

# CSRF trusted origins（從 .env 讀）
CSRF_TRUSTED_ORIGINS = _split_csv_env(
    "CSRF_TRUSTED_ORIGINS",
    "https://land2026.freeddns.org",
)


# =============================================================================
# Static files（由 nginx 提供）
# =============================================================================
STATIC_URL = "/wrehub/static/"
STATIC_ROOT = "/opt/wrehub/staticfiles"


# =============================================================================
# Misc
# =============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


