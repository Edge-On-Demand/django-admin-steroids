
from django import forms
from django.contrib import admin
from django.contrib.admin.sites import site
from django.contrib.admin.widgets import ManyToManyRawIdWidget, ForeignKeyRawIdWidget
from django.core.urlresolvers import reverse, NoReverseMatch
from django.conf import settings
from django.forms.widgets import Select, TextInput, flatatt
from django.template import Context, Template
from django.template.context import Context
from django.utils.encoding import force_unicode, smart_unicode
from django.utils.html import escape
from django.utils.safestring import mark_safe

import utils

try:
    from django.utils.encoding import StrAndUnicode
except ImportError:
    from django.utils.encoding import python_2_unicode_compatible

    @python_2_unicode_compatible
    class StrAndUnicode:
        def __str__(self):
            return self.code

class LinkedSelect(Select):
    def render(self, name, value, attrs=None, *args, **kwargs):
        output = super(LinkedSelect, self).render(name, value, attrs=attrs, *args, **kwargs)
        model = self.choices.field.queryset.model
        to_field_name = self.choices.field.to_field_name or 'id'
        try:
            kwargs = {to_field_name:value}
            obj = model.objects.get(**kwargs)
            view_url = utils.get_admin_change_url(obj)
            output += mark_safe('&nbsp;<a href="%s" target="_blank">view</a>&nbsp;' % (view_url,))
        except model.DoesNotExist:
            pass
        return output

class ForeignKeyTextInput(TextInput):
    """
    Implements the same markup as VerboseForeignKeyRawIdWidget but does not
    require an explicit model relationship.
    """
    
    def __init__(self, model_class, value, *args, **kwargs):
        super(ForeignKeyTextInput, self).__init__(*args, **kwargs)
        self._model_class = model_class
        try:
            value = int(value)
        except ValueError:
            value = 0
        except TypeError:
            value = 0
        self._raw_value = value
        q = model_class.objects.filter(id=value)
        self._instance = None
        if q.count():
            self._instance = q[0]
            
    def render(self, name, value, attrs=None):
        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_unicode(self._format_value(value))
        final_attrs['size'] = 10
        t = Template(u"""
{% load staticfiles %}
<input{{ attrs|safe }} />
{% if instance %}
    <a href="{{ changelist_url|safe }}?t=id" class="related-lookup" id="lookup_{{ id|safe }}" onclick="return showRelatedObjectLookupPopup(this);">
        <img src="{% static 'admin/img/selector-search.gif' %}" width="16" height="16" alt="Lookup" />
    </a>
    <strong><a href="{{ url|safe }}" target="_blank">{{ instance|safe }}</a></strong>
{% endif %}
        """)
        c = Context(dict(
            id=final_attrs['id'],
            attrs=flatatt(final_attrs),
            raw_value=self._raw_value,
            url=utils.get_admin_change_url(self._instance),
            changelist_url=utils.get_admin_changelist_url(self._model_class),
            instance=self._instance,
        ))
        return  mark_safe(t.render(c))

#http://djangosnippets.org/snippets/2217/

class VerboseForeignKeyRawIdWidget(ForeignKeyRawIdWidget):
    
    def __init__(self, *args, **kwargs):
        raw_id_fields_new_tab = True
        if 'raw_id_fields_new_tab' in kwargs:
            raw_id_fields_new_tab = kwargs['raw_id_fields_new_tab']
            del kwargs['raw_id_fields_new_tab']
        super(VerboseForeignKeyRawIdWidget, self).__init__(*args, **kwargs)
        self.raw_id_fields_new_tab = raw_id_fields_new_tab
    
    @property
    def target(self):
        if self.raw_id_fields_new_tab:
            return '_blank'
        return '_self'
    
    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.to._default_manager\
                .using(self.db).get(**{key: value})
            change_url = reverse(
                "admin:%s_%s_change" \
                    % (obj._meta.app_label, obj._meta.object_name.lower()),
                args=(obj.pk,)
            )
            return '&nbsp;<strong><a href="%s" target="%s">%s</a></strong>' \
                % (change_url, self.target, escape(obj))
        except NoReverseMatch:
            return '&nbsp;<strong>%s</strong>' % (escape(obj),)
        except (ValueError, self.rel.to.DoesNotExist):
            return ''

class VerboseManyToManyRawIdWidget(ManyToManyRawIdWidget):
    
    def __init__(self, *args, **kwargs):
        raw_id_fields_new_tab = True
        if 'raw_id_fields_new_tab' in kwargs:
            raw_id_fields_new_tab = kwargs['raw_id_fields_new_tab']
            del kwargs['raw_id_fields_new_tab']
        super(VerboseManyToManyRawIdWidget, self).__init__(*args, **kwargs)
        self.raw_id_fields_new_tab = raw_id_fields_new_tab
    
    @property
    def target(self):
        if self.raw_id_fields_new_tab:
            return '_blank'
        return '_self'
            
    def label_for_value(self, value):
        values = value.split(',')
        str_values = []
        key = self.rel.get_related_field().name
        for v in values:
            obj = self.rel.to._default_manager\
                .using(self.db).get(**{key: v})
            x = smart_unicode(obj)
            try:
                change_url = reverse(
                    "admin:%s_%s_change" \
                        % (obj._meta.app_label, obj._meta.object_name.lower()),
                    args=(obj.pk,)
                )
                str_values += ['<strong><a href="%s" target="%s">%s</a></strong>' \
                    % (change_url, self.target, escape(x))]
            except NoReverseMatch:
                str_values += ['<strong>%s</strong>' % (escape(x),)]
            except self.rel.to.DoesNotExist:
                str_values += [u'???']
        return u', '.join(str_values)

class PlainTextWidget(forms.Widget):
    """
    Renders the value as plain text.
    """
    def render(self, _name, value, attrs=None):
        value = value or ''
        return mark_safe('<div style="padding-top:3px;">'+value+'</div>')

class PreTextWidget(forms.Widget):
    """
    Renders the value as plain text formatted with the "pre" style.
    """
    def render(self, _name, value, attrs=None):
        value = value or ''
        return mark_safe('<div style="padding-top:3px; white-space:pre;">'+value+'</div>')

class NBSPTextWidget(forms.Widget):
    """
    Renders the value as plain text with all spaces replaced by "&nbsp;".
    """
    def render(self, _name, value, attrs=None):
        value = value or ''
        value = value.replace(' ', '&nbsp;').replace('\n', '<br/>')
        return mark_safe('<div style="padding-top:3px;">'+value+'</div>')

class BRTextWidget(forms.Widget):
    """
    Renders the value as plain text with all newlines replaced by "<br/>".
    """
    def render(self, _name, value, attrs=None):
        value = value or ''
        value = value.replace('\n', '<br/>')
        _attrs = self.attrs.copy()
        _attrs.update(attrs or {})
        style = _attrs.get('style', '')
        return mark_safe('<div style="'+style+'">'+value+'</div>')

class ReadOnlyText(forms.TextInput):
    """
    Renders the value as plain text.
    """
    input_type = 'text'

    def render(self, name, value, attrs=None):
        if value is None: 
            value = ''
        return value
