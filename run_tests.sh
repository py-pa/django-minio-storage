#!/bin/sh

pip install -e .
mypy -s --strict-optional minio_storage
coverage run --source=minio_storage tests/manage.py test
OUT=$?
coverage report
coverage html
return $OUT
