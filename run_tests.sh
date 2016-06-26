#!/bin/sh

pip install -e .
coverage run tests/manage.py test
coverage report
coverage html
