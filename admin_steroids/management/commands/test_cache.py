from __future__ import print_function

from django.core.management.base import BaseCommand
try:
    from django.core.cache import caches as _get_cache
except ImportError:
    from django.core.cache import get_cache as _get_cache


def get_cache(name):
    # print('_get_cache:', _get_cache)
    # if isinstance(_get_cache, dict):
    return _get_cache[name]
    # return _get_cache(name)


class Command(BaseCommand):
    args = ''
    help = 'Confirms the cache works.'

    def add_arguments(self, parser):
        parser.add_argument('--name', default='default')
        parser.add_argument('--key', default='key')
        parser.add_argument('--value', default='value')

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
            'Cache failed. Expected %s but cache gave us %s.' % (repr(cache_value), repr(_cache_value))

        print('Cache succeeded.')
