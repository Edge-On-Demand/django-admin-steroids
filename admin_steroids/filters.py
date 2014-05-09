import uuid

from django.conf import settings
from django.contrib.admin import FieldListFilter
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_unicode

class NullListFilter(FieldListFilter):
    
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg = '%s__isnull' % field_path
        self.lookup_val = None
        try:
            self.lookup_val = request.GET.get(self.lookup_kwarg, None)
            if self.lookup_val is not None:
                if self.lookup_val in (True, 'True', 1, '1'):
                    self.lookup_val = True
                else:
                    self.lookup_val = False
        except:
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
        
        super(CachedFieldFilter, self).__init__(field, request, params, model, model_admin, field_path)
        
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
            'display': _('Any'),
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
        self.lookup_val = [_ for _ in request.GET.get(self.lookup_kwarg, '').split(',') if _.strip()]
        
        super(AjaxFieldFilter, self).__init__(field, request, params, model, model_admin, field_path)
        
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
            'display': _('Any'),
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
            if isinstance(self.field, (models.ForeignKey, models.ManyToManyField, models.OneToOneField)):
                rel_model = self.field.rel.to
                #TODO:handle non-numeric IDs?
                value = str(rel_model.objects.get(id=int(value)))
            
            yield {
                'selected': True,
                'query_string': url,
                'display': value,
                'remove_icon': True,
                'alt': 'Remove',
            }
