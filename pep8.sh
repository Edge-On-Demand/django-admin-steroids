#!/bin/bash
VENV=.env
REQS=/tmp/requirements.txt
if [ ! -d $VENV ]; then
    virtualenv $VENV
    . $VENV/bin/activate
    rm -Rf $REQS
    touch $REQS
    cat pip-requirements-min-django.txt >> $REQS
    cat pip-requirements.txt >> $REQS
    cat pip-requirements-test.txt >> $REQS
    $VENV/bin/pip install -r $REQS
fi
. $VENV/bin/activate
pylint --version
pylint --rcfile=pylint.rc admin_steroids setup.py
