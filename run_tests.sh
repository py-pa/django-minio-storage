#!/bin/sh

pip install -e .
mypy -s --strict-optional minio_storage
coverage run tests/manage.py test
OUT=$?
coverage report
coverage html
return $OUT
