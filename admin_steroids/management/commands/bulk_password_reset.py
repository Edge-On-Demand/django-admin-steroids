from __future__ import unicode_literals, print_function

#from urlparse import urlparse
from uuid import uuid4

from six.moves.urllib.parse import urlparse # pylint: disable=import-error

from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS
from django.conf import settings

from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import Site

class Command(BaseCommand):

    help = "Sends the 'forgot your password' reset email for several users."

    def add_arguments(self, parser):
        parser.add_argument('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Specifies the database to use. Default is "default".')
        parser.add_argument('--domain', action='store', dest='domain',
            default=None, help='The domain name of the site. Defaults to settings.BASE_URL')

    def handle(self, *args, **options):

        emails = list(args)

        #is_admin_site = False
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

        secure = hasattr(settings, 'BASE_SECURE_URL') and settings.BASE_SECURE_URL.startswith('https')

        domain = options['domain']
        if not domain:
            try:
                domain = Site.objects.get(id=settings.SITE_ID).domain
            except Exception as e:
                try:
                    domain = urlparse(settings.BASE_URL).netloc
                except Exception as e:
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
