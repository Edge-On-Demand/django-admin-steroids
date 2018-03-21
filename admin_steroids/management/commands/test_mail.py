from __future__ import print_function

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import send_mail

class Command(BaseCommand):
    args = '<message>'
    help = 'Sends a test email to admins.'

    def add_arguments(self, parser):
        parser.add_argument('--subject', default='test subject')
        parser.add_argument('--recipient_list')

    def handle(self, *args, **options):
        from_email = settings.SERVER_EMAIL

        recipient_list = (options.get('recipient_list') or '').strip()
        if recipient_list:
            recipient_list = [_ for _ in recipient_list.split(',') if _.strip()]
        else:
            recipient_list = [email for _, email in settings.ADMINS]

        print('Attempting to send email to %s from %s...' % (', '.join(recipient_list), from_email))
        send_mail(
            subject=options['subject'],
            message=' '.join(args),
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
            auth_user=settings.EMAIL_HOST_USER,
            auth_password=settings.EMAIL_HOST_PASSWORD,
            #connection=None
        )
        print('Sent email to %s.' % (', '.join(recipient_list),))
