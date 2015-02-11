#!/usr/bin/env python
import os
import urllib

from setuptools import setup, find_packages, Command

import admin_steroids

def get_reqs(reqs=["Django>=1.4.0", 'Babel>=1.3']):
    # optparse is included with Python <= 2.7, but has been deprecated in favor
    # of argparse.  We try to import argparse and if we can't, then we'll add
    # it to the requirements
    try:
        import argparse
    except ImportError:
        reqs.append("argparse>=1.1")
    return reqs

setup(
    name = "django-admin-steroids",
    version = admin_steroids.__version__,
    packages = find_packages(),
    package_data = {
        'admin_steroids': [
            'templates/*.*',
            'templates/*/*.*',
            'templates/*/*/*.*',
            'static/*.*',
            'static/*/*.*',
            'static/*/*/*.*',
        ],
    },
    author = "Chris Spencer",
    author_email = "chrisspen@gmail.com",
    description = "",
    license = "LGPL",
    url = "https://github.com/chrisspen/django-admin-steroids",
    #https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers = [
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    zip_safe = False,
    install_requires = get_reqs(),
)
