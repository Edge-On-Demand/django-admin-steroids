"""
Quick test:

    export TESTNAME=.test_delete_duplicate_record; tox -e py27-django15

"""
from __future__ import print_function

import time
import socket
import warnings
import csv

from django.core import mail
from django.test import TestCase
try:
    from django.test import override_settings
except ImportError:
    from override_settings import override_settings

# pylint: disable=C0412
from admin_steroids import utils

warnings.simplefilter('error', RuntimeWarning)

socket.gethostname = lambda: 'localhost'

# Test settings that we don't want to use for all tests.
EMAIL_HOST = 'localhost'
EMAIL_PORT = '1025'
DEV_EMAIL_REDIRECT_TO = 'test@domain.com'
SMTPD_LOG = '/tmp/smtpd.log'

class Tests(TestCase):

#     fixtures = []

    def setUp(self):
        pass

    def test_obj_to_hash(self):
        s = utils.obj_to_hash({123:'abc'})
        self.assertEqual(len(s), 128)

    def test_FormatWithCommas(self):
        s = utils.FormatWithCommas('%.4f', 1234567.5678)
        self.assertEqual(s, '1,234,567.5678')

    @override_settings(EMAIL_BACKEND='admin_steroids.email.DevelopmentEmailBackend')
    @override_settings(EMAIL_HOST=EMAIL_HOST)
    @override_settings(EMAIL_PORT=EMAIL_PORT)
    @override_settings(DEV_EMAIL_REDIRECT_TO=DEV_EMAIL_REDIRECT_TO)
    @override_settings(DEV_EMAIL_APPEND_HOSTNAME=True)
    @override_settings(DEV_EMAIL_ALLOW_ANY_ON_DOMAIN=False)
    def _test_DevelopmentEmailBackend(self):

        # Kill all previous SMTP servers.
#         os.system("ps aux|grep -i smtp|grep -v grep|awk '{print $2}' | xargs -i kill {}")

        # Launch debuggin SMTP server to catch emails.
#         print('a')
#         command = 'python -m smtpd -n -c DebuggingServer %s:%s > %s' \
#             % (EMAIL_HOST, EMAIL_PORT, SMTPD_LOG)
#         print('command:', command)
#         process = subprocess.Popen(command, shell=True)
#         time.sleep(1)
#         print('b')

        output = []

        try:
            #wait_until_response(num=1)

            # Send email.
            self.assertEqual(len(mail.outbox), 0)
            mail.send_mail(
                subject='Subject here',
                message='Here is the message.',
                from_email='from@example.com',
                recipient_list=['to@example.com'],
                fail_silently=False,
            )
            time.sleep(3)

            # Confirm the email didn't go into Django's fake email backend.
            self.assertEqual(len(mail.outbox), 0)

#             last = None
#             t0 = time.time()
#             timeout = 10
#             while 1:
#                 print('checking smtp')
#                 chunk = open(SMTPD_LOG, 'r').read().strip()
#                 if last is not None and last == chunk:
#                     break
#                 last = chunk
#                 time.sleep(1)
#                 if time.time() - t0 > timeout:
#                     break

            # Poll process for new output until finished
            output = '\n'.join(output)
            print('output:', output)

            signature = '(Sent from http://%s)' % EMAIL_HOST
            self.assertTrue(signature in output)

        finally:

            print('Killing SMTP...')
#             if process:
#                 process.kill()
            print('Killed SMTP.')

    def test_csv_encoding(self):
        s = u'\ufffd'

        with self.assertRaises(UnicodeEncodeError):
            print(s.encode('ascii'))

        with self.assertRaises((UnicodeEncodeError, TypeError)):
            with open('/tmp/test.csv', 'wb') as fout:
                writer = csv.DictWriter(fout, fieldnames=['name'])
                writer.writerow({'name': s})

        with open('/tmp/test.csv', 'w') as fout:
            writer = csv.DictWriter(fout, fieldnames=['name'])
            data = utils.encode_csv_data({'name': s})
            print('data:', data)
            writer.writerow(data)

    def test_delete_duplicate_record(self):
        from admin_steroids.tests.models import Person, Contact
        from django.core.management import call_command

        print('Confirming records with no clear conflicts can be merged...')
        Person.objects.all().delete()
        p3 = Person.objects.create(name='Sue')
        Contact.objects.create(person=p3, email='sue@sue.com')
        p4 = Person.objects.create(name='Susan')
        self.assertEqual(Person.objects.all().count(), 2)
        self.assertEqual(Contact.objects.all().count(), 1)
        call_command('delete_duplicate_record', 'tests.person', p4.id, p3.id)
        self.assertEqual(Person.objects.all().count(), 1)
        self.assertEqual(Contact.objects.all().count(), 1)

        print('Confirming records with conflicting dependencies cannot be merged...')
        Person.objects.all().delete()
        self.assertEqual(Person.objects.all().count(), 0)
        self.assertEqual(Contact.objects.all().count(), 0)
        p1 = Person.objects.create(name='Bob')
        Contact.objects.create(person=p1, email='bob@bob.com')
        p2 = Person.objects.create(name='Bobby')
        Contact.objects.create(person=p2, email='bob@bob.com')
        call_command('delete_duplicate_record', 'tests.person', p1.id, p2.id)
        self.assertEqual(Person.objects.all().count(), 2)
        self.assertEqual(Contact.objects.all().count(), 2)

    def test_widgets(self):
        import django
        print('django.version:', django.VERSION)
        from admin_steroids import widgets

    def test_currency(self):
        from admin_steroids.fields import Currency
        value = Currency('$500,000.00')
        self.assertEqual(value, 500000)
        self.assertEqual(value, 500000.0)
        self.assertEqual(value.format(), '500,000.00')
