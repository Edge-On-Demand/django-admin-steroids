from __future__ import print_function

import csv
from inspect import isclass

from django.contrib import admin
from django.contrib.admin.sites import site
from django.forms.models import ModelForm
from django.http import HttpResponse
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe

import six

from .utils import get_admin_change_url
from . import widgets as w
from . import utils
from . import filters

class BaseModelAdmin(admin.ModelAdmin):

#    # Cleanup the breadcrumbs on the change page.
#    def change_view(self, request, object_id, form_url='', extra_context=None):
#        extra_context = extra_context or {}
#        extra_context['app_label'] = self.model._meta.app_label.title()
#        return super(BaseModelAdmin, self).change_view(request, object_id, form_url, extra_context)

    # Cleanup the breadcrumbs on the changelist page.
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['app_label'] = self.model._meta.app_label.title()
        return super(BaseModelAdmin, self).changelist_view(request, extra_context)

    # Cleanup the breadcrumbs on the delete page.
    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}
        extra_context['app_label'] = self.model._meta.app_label.title()
        return super(BaseModelAdmin, self).delete_view(request, object_id, extra_context)

# Based on http://djangosnippets.org/snippets/2217/.
class BetterRawIdFieldsModelAdmin(BaseModelAdmin):
    """
    Displays all raw id fields in a modeladmin as a link going to that record's
    associated admin change page.
    """

    raw_id_fields_new_tab = True

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in self.raw_id_fields:
            kwargs.pop("request", None)
            typ = db_field.rel.__class__.__name__
            if typ == "ManyToOneRel" or typ == "OneToOneRel":
                kwargs['widget'] = w.VerboseForeignKeyRawIdWidget(
                    db_field.rel,
                    site,
                    raw_id_fields_new_tab=self.raw_id_fields_new_tab)
            elif typ == "ManyToManyRel":
                kwargs['widget'] = w.VerboseManyToManyRawIdWidget(
                    db_field.rel,
                    site,
                    raw_id_fields_new_tab=self.raw_id_fields_new_tab)
            return db_field.formfield(**kwargs)
        return super(BetterRawIdFieldsModelAdmin, self)\
            .formfield_for_dbfield(db_field, **kwargs)

ImproveRawIdFieldsForm = BetterRawIdFieldsModelAdmin

class BetterRawIdFieldsTabularInline(admin.TabularInline):
    """
    Displays all raw id fields in a tabular inline as a link going to that
    record's associated admin change page.
    """

    raw_id_fields_new_tab = True

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in self.raw_id_fields:
            kwargs.pop("request", None)
            typ = db_field.rel.__class__.__name__
            if typ == "ManyToOneRel" or typ == "OneToOneRel":
                kwargs['widget'] = w.VerboseForeignKeyRawIdWidget(
                    db_field.rel,
                    site,
                    raw_id_fields_new_tab=self.raw_id_fields_new_tab)
            elif typ == "ManyToManyRel":
                kwargs['widget'] = w.VerboseManyToManyRawIdWidget(
                    db_field.rel,
                    site,
                    raw_id_fields_new_tab=self.raw_id_fields_new_tab)
            return db_field.formfield(**kwargs)
        return super(BetterRawIdFieldsTabularInline, self)\
            .formfield_for_dbfield(db_field, **kwargs)

ImproveRawIdFieldsFormTabularInline = BetterRawIdFieldsTabularInline

class FormatterModelAdmin(BaseModelAdmin):
    """
    Allows the use of per-field formatters.

    Note, inheriting this class requires that the inheritor
    use rename their readonly_fields list to base_readonly_fields.
    This is necessary in order to dynamically insert formatters
    into the readonly_fields list to satisfy the model form field validation.
    """

    base_readonly_fields = ()

    @utils.classproperty
    def readonly_fields(cls):
        # Inserts our formatter instances into the readonly_field list.
        # We need to do this because admin/validation.py line ~243 uses
        # cls.readonly_fields instead of calling get_readonly_fields.
        readonly_fields = list(cls.base_readonly_fields)
        if cls.fieldsets:
            for title, data in cls.fieldsets: # pylint: disable=not-an-iterable
                for name in data['fields']:
                    if callable(name):
                        readonly_fields.append(name)
        elif cls.fields:
            for name in cls.fields: # pylint: disable=not-an-iterable
                if callable(name):
                    readonly_fields.append(name)
        return readonly_fields

    def get_readonly_fields(self, request, obj=None, check_fieldsets=True):
        # Inserts our formatter instances into the readonly_field list.
        readonly_fields = list(self.readonly_fields)
        #fieldsets = self.get_fieldsets(request, obj)
        fieldsets = self.declared_fieldsets
        if fieldsets:
            for title, data in fieldsets:
                for name in data['fields']:
                    if callable(name):
                        readonly_fields.append(name)
        return readonly_fields

class FormatterTabularInline(admin.TabularInline):

    base_readonly_fields = ()

    @utils.classproperty
    def readonly_fields(cls):
        # Inserts our formatter instances into the readonly_field list.
        # We need to do this because admin/validation.py line ~243 uses
        # cls.readonly_fields instead of calling get_readonly_fields.
        readonly_fields = list(cls.base_readonly_fields)
        for name in cls.fields: #pylint: disable=not-an-iterable
            if callable(name):
                readonly_fields.append(name)
        return readonly_fields+['id']

    def get_readonly_fields(self, request, obj=None):
        # Inserts our formatter instances into the readonly_field list.
        readonly_fields = list(self.readonly_fields)
        fieldsets = self.get_fieldsets(request, obj)
        for title, data in fieldsets:
            for name in data['fields']:
                if callable(name):
                    readonly_fields.append(name)
        return readonly_fields

    def id(self, request, obj=None):
        return obj.id

class ReadonlyModelAdmin(BaseModelAdmin):
    """
    Disables all delete or editing functionality in an admin view.
    """

    max_num = 0

    readonly_fields = ()

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super(ReadonlyModelAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields or [])
        exclude = list(self.exclude or [])
        for f in exclude:
            if f in readonly_fields:
                readonly_fields.remove(f)
        return readonly_fields + [f.name for f in self.model._meta.fields if f.name not in exclude]


class NoSaveModelForm(ModelForm):

    def save(self, force_insert=False, force_update=False, commit=True):
        return


class ReadonlyInlineModelAdminMixin(object):

    def get_readonly_fields(self, request, obj=None):
        lst = list(self.readonly_fields)
        lst.extend([f.name for f in self.model._meta.fields])
        return lst

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


class ReadonlyTabularInline(ReadonlyInlineModelAdminMixin, admin.TabularInline):
    form = NoSaveModelForm


class ReadonlyStackedInline(ReadonlyInlineModelAdminMixin, admin.StackedInline):
    form = NoSaveModelForm


def to_ascii(s):
    if not isinstance(s, six.string_types):
        return s
    return s.encode('ascii', errors='replace')


class CSVModelAdminMixin(object):
    """
    Adds a CSV export action to an admin view.
    """

    # This is the maximum number of records that will be written.
    # Be careful about increasing this.
    # Exporting massive numbers of records should be done asynchronously,
    # not in an admin request.
    csv_record_limit = 1000

    # If true, all fields from the queryset will be added to the results.
    csv_headers_all = False

    extra_csv_fields = ()

    # Specifies the header labels, of the form {data_field:header_label}.
    csv_header_names = {}

    csv_quoting = csv.QUOTE_MINIMAL

    # In cases where the default fields contain custom html meant for display in a webpage,
    # strip this out.
    csv_remove_html = True

    def get_actions(self, request):
        if hasattr(self, 'actions') and isinstance(self.actions, list):
            self.actions.append('csv_export')
        if isinstance(self, type) or (isclass(self) and issubclass(self, type)):
            return super(CSVModelAdmin, self).get_actions(request)

    def get_extra_csv_fields(self, request):
        return self.extra_csv_fields

    def get_csv_header_names(self, request):
        return self.csv_header_names

    def get_csv_raw_headers(self, request):
        if self.csv_headers_all:
            all_names = utils.get_model_fields(self.model)
            return all_names + list(self.get_extra_csv_fields(request))
        return list(self.list_display) + list(self.get_extra_csv_fields(request))

    def get_csv_queryset(self, request, qs):
        return qs

    def csv_export(self, request, qs=None, raw_headers=None):
        try:
            response = HttpResponse(mimetype='text/csv')
        except TypeError:
            response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' \
            % slugify(self.model.__name__)

        if raw_headers is None:
            raw_headers = self.get_csv_raw_headers(request)

        def get_attr(obj, name, as_name=False):
            """
            Dereferences "__" delimited variable names.
            """
            parts = name.split('__')
            cursor = obj
            for part in parts:
                name = part
                cursor = getattr(cursor, part, None)
                if callable(cursor):
                    cursor = cursor()
            if cursor == obj:
                return
            if as_name:
                return name
            return cursor

        # Write header.
        header_data = {}
        fieldnames = []
        header_names = self.get_csv_header_names(request)

        # Write records.
        first = True
        qs = self.get_csv_queryset(request, qs)
        for r in qs[:self.csv_record_limit]:

            if first:
                first = False
                if not raw_headers:
                    if self.csv_headers_all and isinstance(r, dict):
                        if isinstance(qs, utils.DictCursor):
                            raw_headers = qs.field_order
                        else:
                            raw_headers = r.keys()
                    else:
                        raise Exception('No headers specified.')
                for name in raw_headers:
                    if name in header_names:
                        name_key = name
                        header_data[name] = header_names.get(name_key)
                    elif callable(name):
                        # This is likely a Formatter instance.
                        name_key = name.name
                        header_data[name_key] = name.short_description
                    elif isinstance(name, (tuple, list)) and len(name) == 2:
                        name_key, name_key_verbose = name
                        header_data[name_key] = name_key_verbose
                    elif isinstance(name, six.string_types) and hasattr(self, name):
                        # This is likely a ModelAdmin method name.
                        name_key = name
                        header_data[name_key] = getattr(self, name).short_description
                    elif hasattr(name, 'short_description'):
                        name_key = name
                        header_data[name_key] = getattr(
                            name, 'short_description')
                    elif hasattr(self.model, name):
                        name_key = name
                        if hasattr(getattr(self.model, name), 'short_description'):
                            header_data[name_key] = getattr(
                                getattr(self.model, name), 'short_description')
                        else:
                            header_data[name_key] = name
                    else:
                        name_key = name
                        header_data[name_key] = name_key#get_attr(r, name, as_name=True)
#                        field = self.model._meta.get_field_by_name(name)
#                        if field and field[0].verbose_name:
#                            header_data[name_key] = field[0].verbose_name
#                        else:
#                            header_data[name_key] = name
                    header_data[name_key] = header_data[name_key].title()
                    fieldnames.append(name_key)

                writer = csv.DictWriter(
                    response,
                    fieldnames=fieldnames,
                    quoting=self.csv_quoting)
                writer.writerow(header_data)
            #print('fieldnames:',fieldnames
            data = {}
            for name in raw_headers:
                obj = None
                if isinstance(r, dict):
                    if name in r:
                        data[name] = r[name]
    #                    print('skipping:',name
                        continue
#                    elif 'id' in r:
#                        obj = self.model.objects.get(id=r['id'])

                if callable(name):
                    # This is likely a Formatter instance.
                    name_key = name.name
                    if hasattr(name, 'plaintext'):
                        data[name_key] = to_ascii(name(r, plaintext=True))
                    else:
                        data[name_key] = to_ascii(name(r))
                elif isinstance(name, (tuple, list)) and len(name) == 2:
                    name_key, name_key_verbose = name
                    if hasattr(self, name_key):
                        data[name_key] = to_ascii(getattr(self, name_key))
                    else:
                        data[name_key] = to_ascii(getattr(r, name_key))
                elif isinstance(name, six.string_types) and hasattr(self, name):
                    # This is likely a ModelAdmin method name.
                    name_key = name
                    data[name_key] = to_ascii(getattr(self, name)(r))
                elif isinstance(name, six.string_types) and hasattr(r, name):
                    name_key = name
                    data[name_key] = to_ascii(getattr(r, name))
                else:
                    name_key = name
                    data[name_key] = to_ascii(get_attr(r, name))

                if callable(data[name_key]):
                    data[name_key] = to_ascii(data[name_key]())

                if self.csv_remove_html:
                    data[name_key] = utils.remove_html(data[name_key])

            #print('data:',data
            #writer.writerow(data)
            writer.writerow(utils.encode_csv_data(data))
        return response
    csv_export.short_description = \
        'Export selected %(verbose_name_plural)s as a CSV file'

class CSVModelAdmin(BaseModelAdmin, CSVModelAdminMixin):

    def get_actions(self, request):
        #TODO:is there a better way to do this? super() ignores the mixin's get_actions()...
        CSVModelAdminMixin.get_actions(self, request)
        return super(CSVModelAdmin, self).get_actions(request)

#https://djangosnippets.org/snippets/2484/
class LogEntryAdmin(ReadonlyModelAdmin):

    list_display = (
        'user',
        'action_time',
        'action',
        'admin_url',
    )

    list_filter = (
        filters.LogEntryAdminUserFilter,
    )

    def get_edited_object(self, obj):
        """
        Returns the edited object represented by this log entry.
        """
        model_class = obj.content_type.model_class()
        if model_class:
            obj = model_class.objects.get(id=obj.object_id)
            return obj

    def admin_url(self, obj=None):
        if not obj or not obj.id:
            return ''
        obj = self.get_edited_object(obj)
        if not obj:
            return ''
        if hasattr(obj, 'get_admin_url'):
            url = obj.get_admin_url()
        else:
            url = get_admin_change_url(obj)
        return mark_safe('<a href="%s">%s</a>' % (url, url))

    def action(self, obj):
        return str(obj)

    @classmethod
    def register(cls, admin_site=None):
        admin_site = admin_site or admin.site
        if hasattr(admin, 'models'):
            admin_site.register(admin.models.LogEntry, LogEntryAdmin)

#admin.site.register(models.LogEntry, LogEntryAdmin)
