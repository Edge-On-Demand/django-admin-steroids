from __future__ import unicode_literals, print_function

import getpass
from optparse import make_option
from urlparse import urlparse
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS
from django.utils.encoding import force_str
from django.conf import settings

from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import Site

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Specifies the database to use. Default is "default".'),
        make_option('--domain', action='store', dest='domain',
            default=None, help='The domain name of the site. Defaults to settings.BASE_URL'),
#        make_option('--site_name', action='store', dest='site_name',
#            default=None, help='The name of the site. Defaults to settings.BASE_URL'),
    )
    help = "Sends the 'forgot your password' reset email for several users."

    def handle(self, *args, **options):
        
        emails = list(args)
        
        is_admin_site = False,
        template_name = 'registration/password_reset_form.html'
        email_template_name = 'registration/password_reset_email.html'
        subject_template_name = 'registration/password_reset_subject.txt'
        password_reset_form = PasswordResetForm
        token_generator = default_token_generator
        post_reset_redirect = None
        from_email = None
        current_app = None
        extra_context = None
        request = None
        
        secure = hasattr(settings, 'BASE_SECURE_URL') \
            and settings.BASE_SECURE_URL.startswith('https')
        
        domain = options['domain']
        if not domain:
            try:
                domain = Site.objects.get(id=settings.SITE_ID).domain
            except:
                try:
                    domain = urlparse(settings.BASE_URL).netloc
                except:
                    pass
                    
#        site_name = options['site_name']
#        if not site_name:
#            try:
#                site_name = Site.objects.get(id=settings.SITE_ID).name
#            except:
#                site_name = domain
        
        for email in emails:
            print('email:', email)
            user = User.objects.get(email=email)
            
            # Ensure the user has some sort of password.
            # Otherwise, the password reset form will ignore it.
            if not user.has_usable_password():
                user.set_password(str(uuid4()))
                user.save()
                
            form = password_reset_form(dict(email=email))
            assert form.is_valid(), 'Invalid email: %s' % email
            opts = {
                'use_https': secure,
                'token_generator': token_generator,
                'from_email': from_email,
                'email_template_name': email_template_name,
                'subject_template_name': subject_template_name,
                'request': request,
                'domain_override': domain,
            }
            form.save(**opts)
            