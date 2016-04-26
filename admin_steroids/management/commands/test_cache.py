from __future__ import print_function

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from optparse import make_option

class Command(BaseCommand):
    args = ''
    help = 'Confirms the cache works.'
    option_list = BaseCommand.option_list + (
        make_option('--name', default='default'),
        make_option('--key', default='key'),
        make_option('--value', default='value'),
    )

    def handle(self, *args, **options):
        from django.core.cache import get_cache
        
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
        