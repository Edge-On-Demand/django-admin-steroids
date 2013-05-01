import csv
        
from django.contrib import admin
from django.contrib.admin.sites import site
from django.http import HttpResponse
from django.template.defaultfilters import slugify

import widgets as w
import utils

class BaseModelAdmin(admin.ModelAdmin):
    
    # Cleanup the breadcrumbs on the change page.
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['app_label'] = self.model._meta.app_label.title()
        return super(BaseModelAdmin, self).change_view(request, object_id, form_url, extra_context)

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
    
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in self.raw_id_fields:
            kwargs.pop("request", None)
            type = db_field.rel.__class__.__name__
            if type == "ManyToOneRel" or type == "OneToOneRel":
                kwargs['widget'] = w.VerboseForeignKeyRawIdWidget(db_field.rel, site)
            elif type == "ManyToManyRel":
                kwargs['widget'] = w.VerboseManyToManyRawIdWidget(db_field.rel, site)
            return db_field.formfield(**kwargs)
        return super(BetterRawIdFieldsModelAdmin, self).formfield_for_dbfield(db_field, **kwargs)

ImproveRawIdFieldsForm = BetterRawIdFieldsModelAdmin

class BetterRawIdFieldsTabularInline(admin.TabularInline):
    """
    Displays all raw id fields in a tabular inline as a link going to that
    record's associated admin change page.
    """
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name in self.raw_id_fields:
            kwargs.pop("request", None)
            type = db_field.rel.__class__.__name__
            if type == "ManyToOneRel" or type == "OneToOneRel":
                kwargs['widget'] = w.VerboseForeignKeyRawIdWidget(db_field.rel, site)
            elif type == "ManyToManyRel":
                kwargs['widget'] = w.VerboseManyToManyRawIdWidget(db_field.rel, site)
            return db_field.formfield(**kwargs)
        return super(BetterRawIdFieldsTabularInline, self).formfield_for_dbfield(db_field, **kwargs)

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
            for title, data in cls.fieldsets:
                for name in data['fields']:
                    if callable(name):
                        readonly_fields.append(name)
        elif cls.fields:
            for name in cls.fields:
                if callable(name):
                    readonly_fields.append(name)
        return readonly_fields

    def get_readonly_fields(self, request, obj=None, check_fieldsets=True):
        # Inserts our formatter instances into the readonly_field list.
        readonly_fields = list(self.readonly_fields)
        #fieldsets = self.get_fieldsets(request, obj)
        fieldsets = self.declared_fieldsets
#        print '!'*80
#        print 'fieldsets:',fieldsets
        if fieldsets:
            for title, data in fieldsets:
                for name in data['fields']:
                    if callable(name):
                        readonly_fields.append(name)
        print '!'*80
        print 'readonly_fields:',readonly_fields
        return readonly_fields

#    def get_fieldsets(self, request, obj=None):
#        "Hook for specifying fieldsets for the add form."
#        if self.declared_fieldsets:
#            return self.declared_fieldsets
#        
#        form = self.get_form(request, obj)
#        fields = form.base_fields.keys() + list(self.get_readonly_fields(request, obj))
#        return [(None, {'fields': fields})]
#    
#        form = self.get_formset(request, obj).form
#        fields = form.base_fields.keys() + list(self.get_readonly_fields(request, obj))
#        return [(None, {'fields': fields})]

class FormatterTabularInline(admin.TabularInline):
        
    base_readonly_fields = ()
    
    @utils.classproperty
    def readonly_fields(cls):
        # Inserts our formatter instances into the readonly_field list.
        # We need to do this because admin/validation.py line ~243 uses
        # cls.readonly_fields instead of calling get_readonly_fields.
        readonly_fields = list(cls.base_readonly_fields)
        for name in cls.fields:
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
        del actions['delete_selected']
        return actions

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)
        return readonly_fields + [f.name for f in self.model._meta.fields]
    
class CSVModelAdmin(BaseModelAdmin):
    """
    Adds a CSV export action to an admin view.
    """
    
    # This is the maximum number of records that will be written.
    # Be careful about increasing this.
    # Exporting massive numbers of records should be done asynchronously,
    # not in an admin request.
    csv_record_limit = 1000
    
    extra_csv_fields = ()
    
    def get_actions(self, request):
        actions = self.actions if hasattr(self, 'actions') else []
        actions.append('csv_export')
        actions = super(CSVModelAdmin, self).get_actions(request)
        return actions
    
    def get_extra_csv_fields(self, request):
        return self.extra_csv_fields
    
    def csv_export(self, request, qs=None):
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' \
            % slugify(self.model.__name__)
        headers = list(self.list_display) + list(self.get_extra_csv_fields(request))
        writer = csv.DictWriter(response, headers)
        
        # Write header.
        header_data = {}
        for name in headers:
            if hasattr(self, name) \
            and hasattr(getattr(self, name), 'short_description'):
                header_data[name] = getattr(
                    getattr(self, name), 'short_description')
            else:
                field = self.model._meta.get_field_by_name(name)
                if field and field[0].verbose_name:
                    header_data[name] = field[0].verbose_name
                else:
                    header_data[name] = name
            header_data[name] = header_data[name].title()
        writer.writerow(header_data)
        
        # Write records.
        for r in qs[:self.csv_record_limit]:
            data = {}
            for name in headers:
                if hasattr(r, name):
                    data[name] = getattr(r, name)
                elif hasattr(self, name):
                    data[name] = getattr(self, name)(r)
                else:
                    raise Exception, 'Unknown field: %s' % (name,)
                    
                if callable(data[name]):
                    data[name] = data[name]()
            writer.writerow(data)
        return response
    csv_export.short_description = \
        'Export selected %(verbose_name_plural)s as CSV'
