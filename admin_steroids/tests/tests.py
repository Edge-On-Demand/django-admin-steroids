from __future__ import print_function

import os
import shlex
import sys
import datetime
from datetime import timedelta
import time
from select import select
import socket
import warnings
import threading
import subprocess
from functools import cmp_to_key

import six

import django
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core import mail
from django.test import TestCase 
from django.test.client import Client
from django.utils import timezone
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
