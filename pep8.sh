#!/bin/bash
. .env/bin/activate
pylint --version
pylint --rcfile=pylint.rc admin_steroids setup.py
