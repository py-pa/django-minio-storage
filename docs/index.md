# About

**django-minio-storage** enables using [minio](https://minio.io) as django
static and media file storages.

Minio is accessed through the Amazon S3 API, so existing django file storage
adapters for S3 should work, but in practice they are hard to configure. This
project uses the minio python client instead. Inspiration has been drawn from
`django-s3-storage` and `django-storages`.

The project source code and issue tracking is hosted at
[github.com/py-pa/django-minio-storage](https://github.com/py-pa/django-minio-storage).

# Compatibility

CI is currenlty executed on Python 3.8+ and Django 3.2+.

The goal is to have a thoroughly tested, small code base that delegates as much
as possible to the minio client.

- Release versioning is semver compliant.
