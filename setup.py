#!/usr/bin/env python
import os

from setuptools import setup, find_packages

import admin_steroids

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))

try:
    with open(os.path.join(CURRENT_DIR, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except TypeError:
    with open(os.path.join(CURRENT_DIR, 'README.md')) as f:
        long_description = f.read()


def get_reqs(*fns):
    lst = []
    for fn in fns:
        for package in open(os.path.join(CURRENT_DIR, fn)).readlines():
            package = package.strip()
            if not package:
                continue
            lst.append(package.strip())
    return lst


setup(
    name="django-admin-steroids",
    version=admin_steroids.__version__,
    packages=find_packages(),
    package_data={
        'admin_steroids': [
            'templates/*.*',
            'templates/*/*.*',
            'templates/*/*/*.*',
            'static/*.*',
            'static/*/*.*',
            'static/*/*/*.*',
        ],
    },
    author="Chris Spencer",
    author_email="chrisspen@gmail.com",
    description="Tweaks and tools to simplify Django admin.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    license="LGPL",
    url="https://gitlab.com/chrisspen/django-admin-steroids",
    #https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.9',
    ],
    zip_safe=False,
    install_requires=get_reqs('pip-requirements-min-django.txt', 'pip-requirements.txt'),
    tests_require=get_reqs('pip-requirements-test.txt'),
)
