from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from config.health import live, ready
from hub import pwa

urlpatterns = [path("sw.js", pwa.worker), path("manifest.webmanifest", pwa.manifest), path("applications-natives/<slug:platform>/", pwa.native, name="native-app"), path("health/live/", live), path("health/ready/", ready), path("admin/", admin.site.urls), path("compte/", include("django.contrib.auth.urls")), path("", include("hub.urls"))]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
