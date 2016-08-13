from __future__ import print_function

import sys

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User

# Based on http://stackoverflow.com/a/954318/247542
class Command(BaseCommand):
    args = ''
    help = 'Forces a specific user to log back in by deleting their session records.'
    option_list = BaseCommand.option_list + (
        make_option('--all', action='store_true', default=False,
            help='If given, all users will be logged out.'),
    )

    def handle(self, *users, **options):
        
        if options['all']:
            
            qs = Session.objects.all()
            total = qs.count()
            i = 0
            for r in qs.iterator():
                i += 1
                sys.stdout.write('\rDeleting session %i of %i...' % (i, total))
                sys.stdout.flush()
                r.delete()
            print('')
        
        else:
            
            for user in users:
                
                print('Looking up user %s...' % user)
                if user.isdigit():
                    user = User.objects.get(id=int(user))
                else:
                    user = User.objects.get(email=user)
                    
                qs = Session.objects.all()
                total = qs.count()
                i = 0
                for s in qs.iterator():
                    i += 1
                    sys.stdout.write('\rChecking user session %i of %i...' % (i, total))
                    sys.stdout.flush()
                    if s.get_decoded().get('_auth_user_id') == user.id:
                        s.delete()
                
        print('Done!')
