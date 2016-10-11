#Currency field borrowed from:
#https://djangosnippets.org/snippets/1527/

import datetime
from decimal import (
    Decimal, InvalidOperation, ROUND_HALF_UP,
)
#from decimal import *

from babel.numbers import (
    format_decimal, format_currency, parse_decimal, parse_number,
    get_decimal_symbol, get_group_symbol, get_currency_symbol,
    NumberFormatError
)

from django import forms
from django.conf import settings
from django.contrib.admin.widgets import AdminDateWidget
#from django.db.models import fields
from django.db import models
#from django.db.models.fields.subclassing import SubfieldBase
#from django.forms import fields, widgets
try:
    from django.forms.util import ValidationError
except ImportError:
    # Renamed in Django 1.9.
    from django.forms.utils import ValidationError 
from django.utils import encoding
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ugettext as _

# The six lib is not included in Django 1.3
# If you have 1.3 (as i have) you can search here in a future version of Django:
# django.utils -> six
import six

default_error_messages = {
    'decimal_symbol': _(u'Ensure that there is only one decimal symbol (%s).'),
    'invalid_format': _(u'Invalid currency format. Please use the format 9%s999%s00')
}

TWOPLACES = Decimal(10) ** -2


def flatatt(attrs):
    """
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs. It is assumed that the keys do not need to be XML-escaped.
    If the passed dictionary is empty, then return an empty string.

    The result is passed through 'mark_safe'.
    """
    return format_html_join('', ' {0}="{1}"', sorted(attrs.items()))


def format_html(format_string, *args, **kwargs):
    # django.utils.html
    """
    Similar to str.format, but passes all arguments through conditional_escape,
    and calls 'mark_safe' on the result. This function should be used instead
    of str.format or % interpolation to build up small HTML fragments.
    """
    args_safe = map(conditional_escape, args)
    kwargs_safe = dict([(k, conditional_escape(v)) for (k, v) in
                        six.iteritems(kwargs)])
    return mark_safe(format_string.format(*args_safe, **kwargs_safe))


def format_html_join(sep, format_string, args_generator):
    # django.utils.html
    """
    A wrapper of format_html, for the common case of a group of arguments that
    need to be formatted using the same format string, and then joined using
    'sep'. 'sep' is also passed through conditional_escape.

    'args_generator' should be an iterator that returns the sequence of 'args'
    that will be passed to format_html.

    Example:

    format_html_join('\n', "<li>{0} {1}</li>", ((u.first_name, u.last_name)
    for u in users))

    """
    return mark_safe(conditional_escape(sep).join(
        format_html(format_string, *tuple(args))
        for args in args_generator))


def is_protected_type(obj):
    return isinstance(obj, six.integer_types + (type(None), float, Decimal,
                                                datetime.datetime, datetime.date, datetime.time))


def force_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    if isinstance(s, six.text_type):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if not isinstance(s, six.string_types):
            if hasattr(s, '__unicode__'):
                s = s.__unicode__()
            else:
                if six.PY3:
                    if isinstance(s, bytes):
                        s = six.text_type(s, encoding, errors)
                    else:
                        s = six.text_type(s)
                else:
                    s = six.text_type(bytes(s), encoding, errors)
        else:
            s = s.decode(encoding, errors)
    except UnicodeDecodeError as e:
        if not isinstance(s, Exception):
            raise encoding.DjangoUnicodeDecodeError(s, *e.args)
        else:
            s = ' '.join([force_text(arg, encoding, strings_only,
                                     errors) for arg in s])
    return s


class CurrencyInput(forms.widgets.TextInput):

    def render(self, name, value, attrs=None):

        if value is None:
            value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            try:
                #value = Currency(value).format()
                value = Currency(value).format_pretty()
            except:
                pass
            final_attrs['value'] = force_unicode(value)

        return mark_safe(u'<input%s />' % flatatt(final_attrs))


def _getSymbols(value):
    retVal = ''
    for x in value:
        if x < u'0' or x > u'9':
            retVal += x
    return retVal


def _getCodes():
    l_currency_language_code = 'en_US'
    l_currency_code = 'USD'
    try:
        l_currency_language_code = settings.CURRENCY_LANGUAGE_CODE
        l_currency_code = ''
    except AttributeError:
        pass
    try:
        l_currency_code = settings.CURRENCY_CODE
    except AttributeError:
        pass

    return (l_currency_language_code, l_currency_code)


def parse_value(value):
    """
    Accepts a string value and attempts to parce it as a currency value.

    Returns the extracted numeric value converted to a string
    """
    l_currency_language_code, l_currency_code = _getCodes()

    curSym = get_currency_symbol(l_currency_code, l_currency_language_code)
    grpSym = get_group_symbol(locale=l_currency_language_code.lower())
    decSym = get_decimal_symbol(locale=l_currency_language_code.lower())

    # Convert the Official characters into what comes from the keyboard.
    #   This section may need to grow over time.
    #   - Character 160 is a non-breaking space, which is different from a typed space
    if ord(grpSym) == 160:
        value = value.replace(u' ', grpSym)

    allSym = _getSymbols(value)
    invalidSym = allSym.replace(curSym, '').replace(
        grpSym, '').replace(decSym, '').replace(u'-', '')

    value = value.replace(curSym, '')

    if allSym.count(decSym) > 1:
        raise NumberFormatError(
            default_error_messages['decimal_symbol'] % decSym)
    elif (allSym.count(decSym) == 1 and allSym[-1] != decSym) or len(invalidSym) > 0:
        raise NumberFormatError(
            default_error_messages['invalid_format'] % (grpSym, decSym))
    elif value.count(decSym) == 1:
        value = parse_decimal(value, locale=l_currency_language_code.lower())
    else:
        value = parse_number(value, locale=l_currency_language_code.lower())

    # The value is converted into a string because the parse functions return
    # floats
    return str(value)


class Currency(Decimal):

    """
    A Currency data type that extends the Decimal type and integrates the Bable libraries.

    Accepts any numeric value or formated currency string as input.


    Testing different numeric inputs and rounding
    >>> Currency(.1)
    Decimal("0.10")
    >>> Currency(1)
    Decimal("1.00")
    >>> Currency(.015)
    Decimal("0.02")
    >>> Currency(.014)
    Decimal("0.01")


    Testing string input and format validation using en_US currency format
    >>> import os
    >>> os.environ['DJANGO_SETTINGS_MODULE'] = 'django.conf.global_settings'
    >>> Currency("1")
    Decimal("1.00")
    >>> Currency("1,234.00")
    Decimal("1234.00")
    >>> Currency("1,234.0.0")
    Traceback (most recent call last):
      ...
    NumberFormatError: Ensure that there is only one decimal symbol (.).
    >>> Currency("1,2,34.0")
    Decimal("1234.00")
    >>> Currency("1,234.00").format()
    u'1,234.00'
    >>> Currency("1,234.00").format_pretty()
    u'$1,234.00'
    >>> Currency("-1,234.00").format_pretty()
    u'$-1,234.00'
    >>> Currency("1 234.00")
    Traceback (most recent call last):
      ...
    NumberFormatError: Invalid currency format. Please use the format 9,999.00
    >>> Currency("1.234,00")
    Traceback (most recent call last):
      ...
    NumberFormatError: Invalid currency format. Please use the format 9,999.00
    >>> Currency("1.234")
    Decimal("1.23")
    >>> Currency("$1,234.00")
    Decimal("1234.00")
    >>> Currency("$1,234.00", format="#,##0").format()
    u'1,234'
    >>> Currency("$-1,234.00", format_pretty=u"#,##0 \xa4").format_pretty()
    u'-1,234 $'


    Testing string input and format validation using pt_BR currency format
    >>> from django.conf import settings
    >>> settings.CURRENCY_LANGUAGE_CODE = 'pt_BR'
    >>> Currency("1 234.00")
    Traceback (most recent call last):
      ...
    NumberFormatError: Invalid currency format. Please use the format 9.999,00
    >>> Currency("1.234")
    Decimal("1234.00")
    >>> Currency("1.234").format()
    u'1.234,00'
    """

    def __new__(cls, value="0", format=None, format_pretty=None, parse_string=False, context=None):
        """
        Create a new Currency object

        value: Can be any number (integer, decimal, or float) or a properly formated string
        format: The format to use in the format() method
        format_pretty: The format used in the format_pretty() method
        parse_string: *IMPORTANT* Set this to True if you are passing a string formatted in a currency 
                      other than the standard decimal format of #,###.##
        context: How to handle a malformed string value
        """
        if value != "0" and isinstance(value, basestring) and parse_string:
            value = parse_value(value)
        elif isinstance(value, float):
            value = str(value)

        if format:
            cls._format = format
        else:
            cls._format = '#,##0.00;-#'

        if format_pretty:
            cls._formatPretty = format_pretty
        else:
            cls._formatPretty = u'\xa4#,##0.00;\xa4-#'

        ld_rounded = Decimal(value or 0).quantize(TWOPLACES, ROUND_HALF_UP)

        return super(Currency, cls).__new__(cls, value=ld_rounded, context=context)

    def format(self):
        l_currency_language_code, l_currency_code = _getCodes()
        return format_decimal(self, format=self._format, locale=l_currency_language_code)

    def format_pretty(self):
        l_currency_language_code, l_currency_code = _getCodes()
        return format_currency(self, l_currency_code, format=self._formatPretty, locale=l_currency_language_code)


class CurrencyFormField(forms.fields.DecimalField):
    
    """
    The form-side companion to CurrencyField, rendering and cleaning
    a dollar-formatting value.
    """

    widget = CurrencyInput

    def __init__(self, *args, **kwargs):
        super(CurrencyFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = (value or '').strip() or None
        if value is None:
            return
        if not self.required and not value:
            return
        try:
            value = Currency(value, parse_string=True)
        except NumberFormatError, e:
            raise ValidationError(e.message)
        return Currency(super(CurrencyFormField, self).clean(value))


class CurrencyField(models.fields.DecimalField):

    """
    A variant of models.DecimalField that formats its value as dollars,
    inserting a dollar-sign and commas as necessary, when rendered on a form.
    """

    #__metaclass__ = SubfieldBase

    def __init__(self,  *args, **kwargs):
        #        if not kwargs.has_key("help_text"):
        #            kwargs['help_text'] = _('Format: ') + Currency(9999.00).format()
        #        decimal_places = 2
        #        if kwargs.has_key('decimal_places'):
        #            del kwargs['decimal_places']
        super(CurrencyField, self).__init__(*args, **kwargs)

    def format(self):
        return Currency(self).format()

    def format_number(self, value):
        return Currency(value).format()

    def formfield(self, **kwargs):
        defaults = {
            'form_class': CurrencyFormField,
        }
        defaults.update(kwargs)
        return super(CurrencyField, self).formfield(**defaults)

    def to_python(self, value):
        if value is None:
            return value
        try:
            return Currency(value)
        except InvalidOperation as e:
            raise InvalidOperation(
                _("This value must be a decimal number."))

    def value_to_string(self, obj):
        val = self._get_val_from_obj(obj)
        if val is None:
            data = ''
        else:
            data = str(val)
        return data

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^admin_steroids\.fields\.CurrencyField"])
except ImportError:
    pass
