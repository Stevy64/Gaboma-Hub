from pathlib import Path
import secrets
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, True))
environ.Env.read_env(BASE_DIR / ".env")
DEBUG = env.bool("DEBUG", default=True)
SECRET_KEY = env("SECRET_KEY", default="")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DÃƒÂ©finir SECRET_KEY et ALLOWED_HOSTS avant d'utiliser DEBUG=false.")
    local_secret = BASE_DIR / ".local-secret"
    try:
        with local_secret.open("x", encoding="utf-8") as stream:
            stream.write(secrets.token_urlsafe(60))
    except FileExistsError:
        pass
    SECRET_KEY = local_secret.read_text(encoding="utf-8").strip()
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost", "testserver"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", default="http://127.0.0.1:8000").rstrip("/")
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "hub",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware",
    "hub.middleware.UniqueVisitorMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True, "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages", "hub.context_processors.hub_context",
    ]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    DATABASES["default"]["OPTIONS"] = {"timeout": 20}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Libreville"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "hub:dashboard"
LOGOUT_REDIRECT_URL = "hub:home"
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Gaboma Hub <noreply@localhost>")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
DATA_UPLOAD_MAX_MEMORY_SIZE = 128 * 1024
# Le tarif de rÃƒÂ©fÃƒÂ©rencement est administrÃƒÂ© via HubAppearance.
for name in ("API_KEY", "API_SECRET", "MERCHANT_ID", "DISBURSEMENT_ID", "LOGO_URL", "WEBHOOK_SECRET"):
    globals()[f"SINGPAY_{name}"] = env(f"SINGPAY_{name}", default="")
SINGPAY_ENVIRONMENT = env("SINGPAY_ENVIRONMENT", default="sandbox")
SINGPAY_BASE_URL = env("SINGPAY_BASE_URL", default="https://gateway.singpay.ga").rstrip("/")
SINGPAY_CHECKOUT_HOSTS = env.list("SINGPAY_CHECKOUT_HOSTS", default=["gateway.singpay.ga", "client.singpay.ga", "pay.singpay.ga"])
SINGPAY_WEBHOOK_TOLERANCE_SECONDS = env.int("SINGPAY_WEBHOOK_TOLERANCE_SECONDS", default=300)
SINGPAY_WEBHOOK_REQUIRE_FRESH_TIMESTAMP = env.bool("SINGPAY_WEBHOOK_REQUIRE_FRESH_TIMESTAMP", default=False)

# Docker: Redis est facultatif pour conserver le dÃƒÂ©marrage local SQLite.
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL, "KEY_PREFIX": "gaboma-hub",
        "OPTIONS": {"socket_connect_timeout": 3, "socket_timeout": 3}}}
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SECURE_REDIRECT_EXEMPT = [r"^health/(live|ready)/$"]
if env.bool("TRUST_PROXY_HEADERS", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": ("django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG else "whitenoise.storage.CompressedManifestStaticFilesStorage")},
}
LOGGING = {"version": 1, "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"}}

# HSTS du hub uniquement : pas d'engagement pour les autres sous-domaines ni preload.
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
