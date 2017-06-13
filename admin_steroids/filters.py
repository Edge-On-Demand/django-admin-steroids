from __future__ import print_function

import uuid

from django.contrib.admin import FieldListFilter, SimpleListFilter, ListFilter
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_text
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.auth.models import User

def get_empty_value_display(cl):
    if hasattr(cl.model_admin, 'get_empty_value_display'):
        return cl.model_admin.get_empty_value_display()
    # Django < 1.9
    from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE # pylint: disable=no-name-in-module
    return EMPTY_CHANGELIST_VALUE

class NullListFilter(FieldListFilter):

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = '%s__isnull' % field_path
        self.lookup_val = None
        try:
            self.lookup_val = request.GET.get(self.lookup_kwarg, None)
            if self.lookup_val is not None:
                if self.lookup_val in (True, 'True', 1, '1'): # pylint: disable=R0102
                    self.lookup_val = True
                else:
                    self.lookup_val = False
        except Exception as e:
            pass
        super(NullListFilter, self).__init__(field,
            request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.lookup_kwarg,]

    def choices(self, cl):
        for lookup, title in (
                (None, _('All')),
                (False, _('Has value')),
                (True, _('Omitted'))):
            d = {
                'selected': self.lookup_val == lookup,
                'query_string': cl.get_query_string({
                    self.lookup_kwarg: lookup,
                }, [self.lookup_kwarg]),
                'display': title,
            }
            yield d

class NullBlankListFilter(FieldListFilter):
    """
    Like NullListFilter, but treats None and '' values synonymously.
    """

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field_path = field_path
        self.lookup_kwarg = '%s_isnullblank' % field_path

        self.lookup_val = None
        try:
            self.lookup_val = request.GET.get(self.lookup_kwarg, None)
            if self.lookup_val is not None:
                if self.lookup_val in (True, 'True', 1, '1'): # pylint: disable=R0102
                    self.lookup_val = True
                else:
                    self.lookup_val = False
        except Exception as e:
            pass

        super(NullBlankListFilter, self).__init__(field,
            request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.lookup_kwarg]

    def queryset(self, request, queryset):
        try:
            if self.lookup_val is True:
                queryset = queryset.filter(
                    Q(**{self.field_path+'__isnull': True})|\
                    Q(**{self.field_path: ''}))
            elif self.lookup_val is False:
                queryset = queryset.exclude(
                    Q(**{self.field_path+'__isnull': True})|\
                    Q(**{self.field_path: ''}))
            return queryset
        except ValidationError as e:
            raise IncorrectLookupParameters(e)

    def choices(self, cl):
        for lookup, title in (
                (None, _('All')),
                (False, _('Has value')),
                (True, _('Omitted'))):
            d = {
                'selected': self.lookup_val == lookup,
                'query_string': cl.get_query_string({
                    self.lookup_kwarg: lookup,
                }, [self.lookup_kwarg]),
                'display': title,
            }
            yield d

class NotInListFilter(FieldListFilter):
    """
    Allows the use of exclude(field=value) via the URL.
    The inverse of Django's default "__in=" URL syntax.
    """

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field_path = field_path
        self.lookup_kwarg = '%s__notin' % field_path
        self.lookup_vals = None
        try:
            self.lookup_vals = request.GET.get(self.lookup_kwarg, None)
            if self.lookup_vals is not None:
                self.lookup_vals = self.lookup_vals.split(',')
        except Exception as e:
            pass

        self.lookup_choices = field.get_choices(include_blank=False)
        super(NotInListFilter, self).__init__(field,
            request, params, model, model_admin, field_path)

        self.title = getattr(field, 'verbose_name', field_path) + ' is not'

    def expected_parameters(self):
        return [self.lookup_kwarg]

    def queryset(self, request, queryset):
        try:
            # Convert the __notin to a Django ORM .exclude(...)
            if self.lookup_kwarg in self.used_parameters and self.lookup_vals:
                queryset = queryset.exclude(**{self.field_path+'__in': self.lookup_vals})
            return queryset
        except ValidationError as e:
            raise IncorrectLookupParameters(e)

    def choices(self, cl):
        yield {
            'selected': self.lookup_vals is None,# and not self.lookup_val_isnull,
            'query_string': cl.get_query_string({},
                [self.lookup_kwarg]),
            'display': _('None'),
        }
        for pk_val, val in self.lookup_choices:
            yield {
                'selected': (smart_text(pk_val) in self.lookup_vals) if self.lookup_vals else False,
                'query_string': cl.get_query_string({
                    self.lookup_kwarg: pk_val,
                }, []),
                'display': val,
            }

class CachedFieldFilter(FieldListFilter):
    """
    Caches the choices query from the model, ignoring any other filtering
    on the model.
    """

    cache_seconds = 3600 # 1-hour

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field_name = field.name
        self.lookup_kwarg = '%s__exact' % field_path
        self.lookup_kwarg2 = '%s__isnull' % field_path
        self.lookup_val = request.GET.get(self.lookup_kwarg, None)
        self.lookup_val2 = request.GET.get(self.lookup_kwarg2, None)

        super(CachedFieldFilter, self).__init__(
            field, request, params, model, model_admin, field_path)

        self.model = model

    def expected_parameters(self):
        return [self.lookup_kwarg, self.lookup_kwarg2]

    def choices(self, cl):
        # Query cached choices.
        # Note, this purposefully gets a distinct set from the global
        # set of values, so that when we cache it, it's valid for all
        # admin queries. Yes, it may include some values that will return
        # no results on some pages, but that's an acceptable trade-off for
        # being able to shave off a lot of query time.
        cache_key = 'cff_%s_%s' \
            % (str(self.model).split("'")[1], self.field_name)
        values = cache.get(cache_key)
        if values is None:
            values = self.model.objects.all()\
                .values_list(self.field_name, flat=True)\
                .distinct().order_by(self.field_name)
            cache.set(cache_key, values, self.cache_seconds)

        yield {
            'selected': self.lookup_val is None and self.lookup_val2 is None,
            'query_string': cl.get_query_string({
                    self.lookup_kwarg2: '',
                }, [self.lookup_kwarg]),
            'display': _('All'),
        }

        for value in values:
            if value is None:
                yield {
                    'selected': self.lookup_val2,
                    'query_string': cl.get_query_string({
                            self.lookup_kwarg: value,
                        }, [self.lookup_kwarg2]),
                    'display': value,
                }
            else:
                yield {
                    'selected': self.lookup_val == value,
                    'query_string': cl.get_query_string({
                            self.lookup_kwarg: value,
                        }, [self.lookup_kwarg2]),
                    'display': value,
                }

class AjaxFieldFilter(FieldListFilter):
    """
    Allows searching for one or more field values via ajax
    and searching for them via __exact or __in.
    """

    template = 'admin_steroids/ajax_filter.html'

    #TODO:specify one-only or multiple
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.field_name = field.name
        self.field = field

        self.lookup_kwarg = '%s__in' % field_path
        self.lookup_val = [
            _ for _ in request.GET.get(self.lookup_kwarg, '').split(',')
            if _.strip()
        ]

        super(AjaxFieldFilter, self).__init__(
            field, request, params, model, model_admin, field_path)

        self.model = model

        self.uuid = '_'+str(uuid.uuid4())

#        _d = request.GET.copy()
#        del _d[self.lookup_kwarg]
#        self.base_url = request.path + '?' + _d.urlencode
#        if _d:
#            self.base_url += '&'
#        self.base_url += self.lookup_kwarg + '='

        self.ajax_url = reverse(
            'model_field_search',
            args=(model._meta.app_label, model.__name__.lower(), self.field_name))

#    def __call__(self, *args, **kwargs):
#        return

    def expected_parameters(self):
        return [self.lookup_kwarg]

    @property
    def values(self):
        return self.lookup_val

    def choices(self, cl):
        # Note, all these choices are for *deselecting* the value.
        # Additions will be handled dynamically via AJAX.
        yield {
            'selected': not self.lookup_val,
            'query_string': cl.get_query_string(
                new_params={},
                remove=[self.lookup_kwarg],
            ),
            'display': _('All'),
            'remove_icon': False,
            'alt': 'Remove All',
        }
        for value in self.values:
            lst_without = list(self.lookup_val)
            lst_without.remove(value)

            if lst_without:
                url = cl.get_query_string(
                    new_params={self.lookup_kwarg: ','.join(lst_without)},
                    remove=[self.lookup_kwarg],
                )
            else:
                url = cl.get_query_string(
                    new_params={},
                    remove=[self.lookup_kwarg],
                )

            # Lookup the "pretty" display value for IDs of related models.
            if isinstance(self.field,
                (
                    models.ForeignKey,
                    models.ManyToManyField,
                    models.OneToOneField,
                )):
                rel_model = self.field.rel.to
                #TODO:handle non-numeric IDs?
                # AvB edit here; some FK models do not have an (integer) or .id attribute!
                #value = str(rel_model.objects.get(id=int(value)))
                if value.isdigit():
                    value = int(value)
                value = str(rel_model.objects.get(pk=value))

            yield {
                'selected': True,
                'query_string': url,
                'display': value,
                'remove_icon': True,
                'alt': 'Remove',
            }

class LogEntryAdminUserFilter(SimpleListFilter):
    title = _('user')
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        qs = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True))
        qs = qs.order_by('username')
        return [(user.pk, _(str(user))) for user in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user__pk=self.value())

        return queryset

#http://stackoverflow.com/a/20588975/247542
class SingleTextInputFilter(ListFilter):
    """
    renders filter form with text input and submit button
    """
    size = 40
    parameter_name = None
    template = 'admin_steroids/textinput_filter.html'
    style = ''

    def __init__(self, request, params, model, model_admin):
        super(SingleTextInputFilter, self).__init__(
            request, params, model, model_admin)
        if self.parameter_name is None:
            raise ImproperlyConfigured(
                "The list filter '%s' does not specify "
                "a 'parameter_name'." % self.__class__.__name__)

        if self.parameter_name in params:
            value = params.pop(self.parameter_name)
            self.used_parameters[self.parameter_name] = value

    def value(self):
        """
        Returns the value (in string format) provided in the request's
        query string for this filter, if any. If the value wasn't provided then
        returns None.
        """
        return self.used_parameters.get(self.parameter_name, None)

    def has_output(self):
        return True

    def expected_parameters(self):
        """
        Returns the list of parameter names that are expected from the
        request's query string and that will be used by this filter.
        """
        return [self.parameter_name]

    def queryset(self, request, queryset):
        raise NotImplementedError

    def choices(self, cl):
        all_choice = {
            'selected': self.value() is None,
            'query_string': cl.get_query_string({}, [self.parameter_name]),
            'display': _('All'),
        }
        v = self.value()
        return ({
            'get_query': cl.params,
            'current_value': '' if v is None else v,
            'all_choice': all_choice,
            'parameter_name': self.parameter_name,
            'query_string': all_choice['query_string'],
            'title': self.title,
            'size': self.size,
            'style': self.style,
        }, )
