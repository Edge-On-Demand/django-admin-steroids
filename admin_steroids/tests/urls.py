from django.conf.urls import url, include
from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured


admin.autodiscover()

try:
    urlpatterns = [
        url(r'^admin/', include(admin.site.urls)),
    ]
except ImproperlyConfigured:
    urlpatterns = [
        url(r'^admin/', admin.site.urls),
    ]
