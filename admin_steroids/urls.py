"""
URLs.
"""

try:
    # Removed in Django 1.6
    from django.conf.urls.defaults import url
except ImportError:
    from django.conf.urls import url

try:
    # Relocated in Django 1.6
    from django.conf.urls.defaults import patterns
except ImportError:
    # Completely removed in Django 1.10
    try:
        from django.conf.urls import patterns
    except ImportError:
        patterns = None

from admin_steroids import views

_patterns = [
    url(
        r'^(?P<app_name>[^/]+)/(?P<model_name>[^/]+)/field/(?P<field_name>[^/]+)/search/?',
        views.ModelFieldSearchView.as_view(),
        # If you override this, be sure to use the same name, so reverse() still works.
        name='model_field_search'),
]

if patterns is None:
    urlpatterns = _patterns
else:
    urlpatterns = patterns('', *_patterns)
