from __future__ import print_function

from optparse import make_option

from django.core.management.base import BaseCommand
try:
    from django.core.cache import caches as _get_cache
except ImportError:
    from django.core.cache import get_cache as _get_cache

def get_cache(name):
    if isinstance(_get_cache, dict):
        return _get_cache[name]
    return _get_cache(name)

class Command(BaseCommand):
    args = ''
    help = 'Confirms the cache works.'
    option_list = BaseCommand.option_list + (
        make_option('--name', default='default'),
        make_option('--key', default='key'),
        make_option('--value', default='value'),
    )

    def handle(self, *args, **options):

        cache = get_cache(options['name'])
        cache_key = options['key']
        cache_value = options['value']

        cache.delete(cache_key)
        _cache_value = cache.get(cache_key)
        assert _cache_value is None

        cache.set(cache_key, cache_value, 60)
        _cache_value = cache.get(cache_key)
        assert _cache_value == cache_value, \
            'Cache failed. Expected %s but cache gave us %s.' \
                % (repr(cache_value), repr(_cache_value))

        print('Cache succeeded.')
