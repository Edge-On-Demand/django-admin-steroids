from django.contrib import admin
from django.urls import re_path, include


admin.autodiscover()

urlpatterns = [
    re_path(r'^admin/', include(admin.site.urls)),
]
