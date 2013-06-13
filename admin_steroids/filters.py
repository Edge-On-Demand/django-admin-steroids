
from django.conf import settings
from django.contrib.admin import FieldListFilter
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
            