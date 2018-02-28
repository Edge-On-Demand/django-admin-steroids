#!/bin/bash
# Runs all tests.
set -e
./pep8.sh
rm -Rf .tox
export TESTNAME=; tox
