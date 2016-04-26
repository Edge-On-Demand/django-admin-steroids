import re
import hashlib

from six.moves import cPickle as pickle

from django.conf import settings
from django.db import models

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse, NoReverseMatch

def obj_to_hash(o):
    """
    Returns the 128-character SHA-512 hash of the given object's Pickle
    representation.
    """
    return hashlib.sha512(pickle.dumps(o)).hexdigest()

def get_admin_change_url(obj):
    """
    Returns the admin change url associated with the given instance.
    """
    if obj is None:
        return
    try:
        ct = ContentType.objects.get_for_model(obj, for_concrete_model=False)
        obj_cls = type(obj)
        if hasattr(obj_cls, 'app_label_name'):
            app_label = obj_cls.app_label_name
        else:
            app_label = ct.app_label
        change_url_name = 'admin:%s_%s_change' % (app_label, ct.model)
        return reverse(change_url_name, args=(obj.id,))
    except:
        raise
    
def get_admin_add_url(obj, for_concrete_model=False):
    """
    Returns the admin add url associated with the given instance.
    """
    if obj is None:
        return
    try:
        ct = ContentType.objects.get_for_model(
            obj,
            for_concrete_model=for_concrete_model)
        list_url_name = 'admin:%s_%s_add' % (ct.app_label, ct.model)
        try:
            return reverse(list_url_name)
        except NoReverseMatch:
            # If this is a proxy model and proxy support is on, try to return
            # the parent changelist.
            if not for_concrete_model:
                return get_admin_add_url(obj, for_concrete_model=True)
            else:
                raise
    except:
        raise

def get_admin_changelist_url(obj, for_concrete_model=False):
    """
    Returns the admin changelist url associated with the given instance.
    """
    if obj is None:
        return
    try:
        ct = ContentType.objects.get_for_model(
            obj,
            for_concrete_model=for_concrete_model)
        list_url_name = 'admin:%s_%s_changelist' % (ct.app_label, ct.model)
        try:
            return reverse(list_url_name)
        except NoReverseMatch:
            # If this is a proxy model and proxy support is on, try to return
            # the parent changelist.
            if not for_concrete_model:
                return get_admin_changelist_url(obj, for_concrete_model=True)
            else:
                raise
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

def absolutize_all_urls(
    text,
    domain=None,
    overwrite_domain=False,
    protocol='http',
    overwrite_protocol=True,
    url_pattern='(?:href|src)=[\'"](/+.*?)[\'"]'):
    """
    Inserts a domain and protocol into all href and src URLs missing them.
    """
    import re
    from urlparse import urlparse
    if not domain:
        from django.conf import settings
        domain = urlparse(settings.BASE_URL).netloc
    matches = re.findall(url_pattern, text)
    for old_url in matches:
        result = urlparse(old_url)
        result = result._replace(
            scheme=(not overwrite_protocol and netloc.scheme) or protocol,
            netloc=(not overwrite_domain and result.netloc) or domain)
        new_url = result.geturl()
        text = text.replace(old_url, new_url)
    return text

def view_link(url, obj=None, target='_blank', prefix='', template='', view_str='', class_str=''):
    """
    Returns the HTML for a simple link referring to a page of items,
    usually showing a count.
    
    Meant to be applied to ForeignKey fields on the given object.
    """
    class_str = class_str or 'button'
    count = 0
    if isinstance(url, models.Model):
        obj = url
        view_str = view_str or str(obj)
        url = get_admin_change_url(obj)
    elif isinstance(obj, (int, float)):
        view_str = view_str or ('View %s' % (obj,))
        count = obj
    elif obj:
        view_str = view_str or (prefix + str(obj))
    else:
        view_str = view_str or 'View'
        
    if template:
        view_str = template.format(count=count)
        
    return '<a href=\"{url}\" target=\"{tgt}\" class="{class_str}">{view}</a>'\
        .format(url=url, view=view_str.replace(' ', '&nbsp;'), tgt=target, class_str=class_str)

def view_related_link(obj, field_name, reverse_field=None, extra='', template='', **kwargs):
    """
    Returns the HTML for rendering a link to a related model's
    admin changelist page.
    
    Meant to be applied to ForeignKey fields on a related object where field_name
    is the related_name associated with the ForiegnKey pointing to the given object.
    """
    related = getattr(obj, field_name)
    model = related.model
    q = related.all()
    
    #TODO:is there a more efficient way to do this?
    if not reverse_field:
        reverse_fields = [
            _.name for _ in model._meta.fields
            if _.rel and _.rel.to == type(obj) and _.rel.related_name == field_name
        ]
#        print('field_name:',field_name
#        for _ in model._meta.fields:
#            if 'foreignkey' in str(_).lower():
#                print(_.rel.related_name
        
        if not reverse_fields:
            reverse_fields = [
                _.name for _ in model._meta.fields
                if _.rel and _.rel.to == type(obj)
            ]
        
#        print('related model:',model
#        print('fields:',[_.name for _ in model._meta.fields]
#        print('obj:',obj
#        print('field_name:',field_name
#        print('reverse_fields:',reverse_fields
        assert len(reverse_fields) == 1, 'Ambiguous reverse_field for %s: %s' % (field_name, reverse_fields,)
        reverse_field = reverse_fields[0]

    url = get_admin_changelist_url(model) + '?' + reverse_field + '=' + str(obj.pk)
    
    if extra:
        if not extra.startswith('&'):
            extra = '&'+extra
        url = url + extra
    
    return view_link(url, q.count(), template=template, **kwargs)

def dereference_value(obj, name, as_name=False):
    """
    Given a Django model instance and an underscore-separated name,
    looks up the associated value.
    """
    parts = name.split('__')
    cursor = obj
    for part in parts:
        cursor = getattr(cursor, part, None)
        if callable(cursor):
            cursor = cursor()
    if cursor == obj:
        return
    if as_name:
        return name
    return cursor

class DictCursor(object):
    """
    A database cursor that returns records as dictionaries,
    using the field names as keys.
    """
    def __init__(self, database_name='default'):
        from django.db import connections
        self.cursor = connections[database_name].cursor()
        self._results = None
    def execute(self, *args, **kwargs):
        self.cursor.execute(*args, **kwargs)
        self.desc = self.cursor.description
    @property
    def field_order(self):
        return [_[0] for _ in self.desc]
    def __getitem__(self, i):
        lst = []
        j = 0
        for r in self:
            j += 1
            if j > i:
                break
            lst.append(r)
        return lst
    def fetchall(self):
        return list(self)
    def __iter__(self):
        desc = self.cursor.description
        for row in self.cursor.fetchall():
            yield dict(zip([col[0] for col in desc], row))

def count_related_objects(obj):
    """
    Counts the number of records pointing to the given object via ForeignKey fields.
    """
    cnt = 0
    links = obj._meta.get_all_related_objects()
    for link in links:
        if not link.model._meta.managed:
            continue
        referring_objects = getattr(obj, link.get_accessor_name()).all()
        cnt += referring_objects.count()
    return cnt

def remove_html(s):
    import HTMLParser
    
    s = unicode(s)
    
    # We do this ourselves since HTMLParser does not convert this to the ASCII
    # blank space character.
    s = s.replace('&nbsp;', ' ')
    
    # Strip out all other HTML entities.
    s = HTMLParser.HTMLParser().unescape(s)
    
    try:
        # Try using BeautifulSoup to strip out HTML, since its parser is more robust
        # than a simple Regex.
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(s)
        s = ''.join(soup.findAll(text=True))
    except ImportError:
        # However, if the user doesn't want another dependency, fallback to Regex.
        s = re.sub("<.*?>", '', s)
        
    return s
    