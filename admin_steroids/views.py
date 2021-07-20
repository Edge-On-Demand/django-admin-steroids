import json
import operator

from django.views.generic.base import TemplateView
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

import six

from admin_steroids.models import get_modelsearcher


class ModelFieldSearchView(TemplateView):
    """
    Allows searching for field values in an arbitrary model for dynamically
    populating admin list filters.
    """

    @property
    def search_path_tuple(self):
        return (
            self.kwargs['app_name'],
            self.kwargs['model_name'],
            self.kwargs['field_name'],
        )

    @property
    def q(self):
        return self.request.GET.get('q', '').strip()

    @property
    def model(self):
        ct = ContentType.objects.get(app_label=self.kwargs['app_name'], model=self.kwargs['model_name'])
        return ct.model_class()

    @property
    def cache_key(self):
        return self.search_path_tuple + (self.q,)

    def render_to_response(self, context, **response_kwargs):

        path = self.search_path_tuple
        if path not in settings.DAS_ALLOWED_AJAX_SEARCH_PATHS:
            raise PermissionDenied

        # Ensure only authorized users can access admin URLs.
        #TODO:extend this to allow custom authentication options
        if 'admin' in self.request.path:
            if not self.request.user.is_authenticated:
                raise PermissionDenied
            if not self.request.user.is_active:
                raise PermissionDenied
            if not self.request.user.is_staff:
                raise PermissionDenied

        cache_key = self.cache_key

        model = self.model
        q = self.q
        field_name = self.kwargs['field_name']
        n = settings.DAS_MAX_AJAX_SEARCH_RESULTS
        results = []
        if q:
            field = model._meta.get_field(field_name)
            field_type = type(field)

            cb = get_modelsearcher(
                app_label=self.kwargs['app_name'],
                model_name=self.kwargs['model_name'],
                field_name=field_name,
            )
            if cb:
                # Lookup field values using a custom callback if provided.
                qs = cb(
                    app_label=self.kwargs['app_name'],
                    model_name=self.kwargs['model_name'],
                    field_name=field_name,
                    q=q,
                ) or []
                qs = qs[:n]
                results = [dict(key=_.id if hasattr(_, 'id') else _, value=str(_), field_name=field_name) for _ in qs]
            elif isinstance(field, (
                models.CharField,
                models.EmailField,
                models.SlugField,
                models.TextField,
                models.URLField,
            )):

                # Build query for a simple string-based field.
                qs = model.objects.filter(**{field_name+'__icontains': q})\
                    .values_list(field_name, flat=True)\
                    .order_by(field_name)\
                    .distinct()
                qs = qs[:n]
                results = [dict(key=_, value=_, field_name=field_name) for _ in qs]

            elif isinstance(field, (
                models.ForeignKey,
                models.ManyToManyField,
                models.OneToOneField,
            )):
                # Build query for a related model.
                search_fields = settings.DAS_AJAX_SEARCH_PATH_FIELDS.get(path)
                if search_fields:
                    qs_args = []
                    for search_field in search_fields:
                        #qs_args.append(Q(**{field_name+'__'+search_field+'__icontains': q}))
                        qs_args.append(Q(**{search_field + '__icontains': q}))
                    rel_model = field.remote_field.model
                    qs = rel_model.objects.filter(six.moves.reduce(operator.or_, qs_args))
                    qs = qs[:n]
                    pk_name = rel_model._meta.pk.name
                    results = [dict(key=getattr(_, pk_name), value=str(_), field_name=field_name) for _ in qs.iterator()]

        response = HttpResponse(json.dumps(results), content_type='application/json', **response_kwargs)
        if settings.DAS_AJAX_SEARCH_DEFAULT_CACHE_SECONDS:
            cache.set(cache_key, response, settings.DAS_AJAX_SEARCH_DEFAULT_CACHE_SECONDS)
        return response
