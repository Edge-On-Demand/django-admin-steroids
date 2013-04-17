import re

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

def get_admin_change_url(obj):
    if obj is None:
        return
    try:
        ct = ContentType.objects.get_for_model(obj)
        obj_cls = type(obj)
        if hasattr(obj_cls, 'app_label_name'):
            app_label = obj_cls.app_label_name
        else:
            app_label = ct.app_label
        change_url_name = 'admin:%s_%s_change' % (app_label, ct.model)
        return reverse(change_url_name, args=(obj.id,))
    except:
        raise

def get_admin_changelist_url(obj):
    if obj is None:
        return
    try:
        ct = ContentType.objects.get_for_model(obj)
        list_url_name = 'admin:%s_%s_changelist' % (ct.app_label, ct.model)
        return reverse(list_url_name)
    except:
        raise

class StringWithTitle(str):
    """
    String class with a title method. Can be used to override 
    admin app names.

    http://ionelmc.wordpress.com/2011/06/24/custom-app-names-in-the-django-admin/
    """

    def __new__(cls, value, title):
        instance = str.__new__(cls, value)
        instance._title = title
        return instance

    def title(self):
        return self._title

    __copy__ = lambda self: self
    __deepcopy__ = lambda self, memodict: self

re_digits_nondigits = re.compile(r'\d+|\D+')

def FormatWithCommas(format, value):
    """
    >>> FormatWithCommas('%.4f', .1234)
    '0.1234'
    >>> FormatWithCommas('%i', 100)
    '100'
    >>> FormatWithCommas('%.4f', 234.5678)
    '234.5678'
    >>> FormatWithCommas('$%.4f', 234.5678)
    '$234.5678'
    >>> FormatWithCommas('%i', 1000)
    '1,000'
    >>> FormatWithCommas('%.4f', 1234.5678)
    '1,234.5678'
    >>> FormatWithCommas('$%.4f', 1234.5678)
    '$1,234.5678'
    >>> FormatWithCommas('%i', 1000000)
    '1,000,000'
    >>> FormatWithCommas('%.4f', 1234567.5678)
    '1,234,567.5678'
    >>> FormatWithCommas('$%.4f', 1234567.5678)
    '$1,234,567.5678'
    >>> FormatWithCommas('%i', -100)
    '-100'
    >>> FormatWithCommas('%.4f', -234.5678)
    '-234.5678'
    >>> FormatWithCommas('$%.4f', -234.5678)
    '$-234.5678'
    >>> FormatWithCommas('%i', -1000)
    '-1,000'
    >>> FormatWithCommas('%.4f', -1234.5678)
    '-1,234.5678'
    >>> FormatWithCommas('$%.4f', -1234.5678)
    '$-1,234.5678'
    >>> FormatWithCommas('%i', -1000000)
    '-1,000,000'
    >>> FormatWithCommas('%.4f', -1234567.5678)
    '-1,234,567.5678'
    >>> FormatWithCommas('$%.4f', -1234567.5678)
    '$-1,234,567.5678'
    
    """
    parts = re_digits_nondigits.findall(format % (value,))
    for i in xrange(len(parts)):
        s = parts[i]
        if s.isdigit():
            parts[i] = _commafy(s)
            break
    return ''.join(parts)
    
def _commafy(s):
    r = []
    for i, c in enumerate(reversed(s)):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    return ''.join(r)

def currency_value(value, decimal_places=2):
    """
    Convert a given value to a standard currency value.
    """
    import decimal
 
    # Build the template for quantizing the decimal places.
    q = '0.' + ('0' * (decimal_places-1)) + '1'

    # Use the Decimal package to get the proper fixed point value.
    with decimal.localcontext() as context:
        try:
            context.rounding = decimal.ROUND_HALF_UP
            return decimal.Decimal(value).quantize(decimal.Decimal(q), 
                                                   decimal.ROUND_HALF_UP)
        except:
            return None

class classproperty(object):
    """
    Implements a @property-like decorator for class methods.
    """
    def __init__(self, getter):
        self.getter= getter
    def __get__(self, instance, owner):
        return self.getter(owner)
    