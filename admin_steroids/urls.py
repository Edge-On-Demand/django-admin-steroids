from django.urls import re_path

from . import views

urlpatterns = [
    re_path(
        r'^(?P<app_name>[^/]+)/(?P<model_name>[^/]+)/field/(?P<field_name>[^/]+)/search/?',
        views.ModelFieldSearchView.as_view(),
        # If you override this, be sure to use the same name, so reverse() still works.
        name='model_field_search'
    ),
]
