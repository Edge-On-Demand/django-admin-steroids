"""
URLs.
"""
from django.conf.urls import patterns, url

import views

urlpatterns = patterns('admin_steroids.views',
    url(
        r'^(?P<app_name>[^/]+)/(?P<model_name>[^/]+)/field/(?P<field_name>[^/]+)/search/?',
        views.ModelFieldSearchView.as_view(),
        # If you override this, be sure to use the same name, so reverse() still works.
        name='model_field_search'),
)
