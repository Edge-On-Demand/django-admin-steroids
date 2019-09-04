#!/bin/bash
# Note, this should be used rarely, and instead the pre-commit hook relied upon.
yapf --in-place --recursive admin_steroids
yapf --in-place --recursive setup.py
