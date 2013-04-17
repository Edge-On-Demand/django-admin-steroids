#!/usr/bin/env python
import os
import urllib

from setuptools import setup, find_packages, Command

VERSION = (0, 1, 1)
__version__ = '.'.join(map(str, VERSION))

def get_reqs(reqs=["Django>=1.4.0"]):
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
    version = __version__,
    packages = find_packages(),
    author = "Chris Spencer",
    author_email = "chrisspen@gmail.com",
    description = "",
    license = "LGPL",
    url = "https://github.com/chrisspen/django-admin-steroids",
    classifiers = [
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: LGPL License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ],
    zip_safe = False,
    install_requires = get_reqs(),
)
