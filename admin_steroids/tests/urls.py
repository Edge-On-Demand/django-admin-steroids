
from django.conf.urls import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('admin_steroids.tests.views',
    (r'^admin/', include(admin.site.urls)),
)
