from __future__ import print_function

import os
import datetime
from datetime import timedelta
import time
import socket
import threading
from functools import cmp_to_key

socket.gethostname = lambda: 'localhost'

import six

import django
from django.core.management import call_command
from django.core import mail
from django.test import TestCase
from django.test.client import Client
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings

from admin_steroids import utils

import warnings
warnings.simplefilter('error', RuntimeWarning)

class Tests(TestCase):
    
#     fixtures = []
    
    def setUp(self):
        pass
    
    def test_obj_to_hash(self):
        s = utils.obj_to_hash({123:'abc'})
        self.assertEqual(len(s), 128)
        