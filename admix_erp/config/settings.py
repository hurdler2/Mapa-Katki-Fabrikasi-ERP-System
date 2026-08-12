"""ADMIX-ERP Django ayarları.

Env-tabanlı: DB_ENGINE=postgres → PostgreSQL, aksi halde SQLite.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "1" if default else "0").lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-secret-change-me")
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "simple_history",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    # yerel app'ler
    "common",
    "masterdata",
    "formulation",
    "inventory",
    "production",
    "quality",
    "purchasing",
    "sales",
    "reporting",
    "scada",
    "iam",
    "qms",
    "docs",
    "governance",
    "chemicals",
    "ehs",
    "cmms",
    "accounting",
    "mrp",
    "hr",
    "notifications",
    "api",
    "analytics",
    "lims",
    "portal",
    "businessline",
    "registry",
    "records",
]

# MCOS uyum fazları — her faz GM tarafından ayrı aktive edilir (audit trail).
# Feature flag'ler: kod yayında ama davranış açık/kapalı.
MCOS_ENABLE_BUSINESSLINE = os.environ.get(
    "MCOS_ENABLE_BUSINESSLINE", "1").lower() in {"1", "true", "yes", "on"}
MCOS_ENABLE_CONTROLLED_CODE = os.environ.get(
    "MCOS_ENABLE_CONTROLLED_CODE", "1").lower() in {"1", "true", "yes", "on"}
MCOS_ENABLE_5LAYER_ID = os.environ.get(
    "MCOS_ENABLE_5LAYER_ID", "1").lower() in {"1", "true", "yes", "on"}
MCOS_ENABLE_GATE = os.environ.get(
    "MCOS_ENABLE_GATE", "0").lower() in {"1", "true", "yes", "on"}
MCOS_ENABLE_RETRIEVAL = os.environ.get(
    "MCOS_ENABLE_RETRIEVAL", "0").lower() in {"1", "true", "yes", "on"}
MCOS_ENABLE_MASTER_REGISTER = os.environ.get(
    "MCOS_ENABLE_MASTER_REGISTER", "0").lower() in {"1", "true", "yes", "on"}
MCOS_ENABLE_RULES_ENFORCER = os.environ.get(
    "MCOS_ENABLE_RULES_ENFORCER", "0").lower() in {"1", "true", "yes", "on"}

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# SCADA köprüsü ayarları (Faz 6)
# Gerçek adapter'lar yalnız SCADA_ENABLED=1 iken çalışır; aksi halde MockAdapter.
SCADA_ENABLED = os.environ.get("SCADA_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
SCADA_DEFAULT_ADAPTER = os.environ.get("SCADA_DEFAULT_ADAPTER", "mock")  # mock | opcua | modbus | mqtt

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "portal.context_processors.portal_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Veritabanı: env tabanlı seçim
if os.environ.get("DB_ENGINE", "sqlite").lower() == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "admix_erp"),
            "USER": os.environ.get("POSTGRES_USER", "admix"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "admix"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# @login_required decorator'ları markalı /login/ sayfasına yönlendirir
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

# Desteklenen diller (kullanıcı profiline göre değiştirilebilir).
LANGUAGES = [
    ("tr", "Türkçe"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
