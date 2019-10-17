# About

**django-minio-storage** enables using [minio](https://minio.io) as django
static and media file storages.

Minio is accessed through the Amazon S3 API, so existing django file storage
adapters for S3 should work, but in practice they are hard to configure. This
project uses the minio python client instead. Inspiration has been drawn from
`django-s3-storage` and `django-storages`.

# Compatibility

CI is currenlty executed on Python 3.6+ and Django 1.11+.

The goal is to have a thoroughly tested, small code base that delegates as much
as possible to the minio client.

- Release versioning is semver compliant.
