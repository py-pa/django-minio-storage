# django-minio-storage

[![Build Status](https://travis-ci.org/py-pa/django-minio-storage.svg?branch=master)](https://travis-ci.org/py-pa/django-minio-storage)

# IMPORTANT NOTE ABOUT THIS FORK

- This is a fork https://github.com/tomhoule/django-minio-storage with fixes
  and improvements.

- The final goal of this fork is do fixes and make the project ready to be
  maintained by [jazzband](https://jazzband.co/).

- Avoiding forking is always preferable so if the original maintainer can get
  involved in this process we would be very happy.

- This fork attempts to not break API's which exists in release versions unless
  the API's themselves are broken.

- This fork currently does not officially support python 2, if the original
  maintainer gets involved and strongly disagree with this decision py2 support
  can be reinstated (No active removal has been done except for the Travis)

- Depending on future maintainer circumstances **this repository might be fully
  removed or moved** and **the -py-pa suffixed packages released to pypi.org
  will stop being published and in removed 6 months after the last published
  version.**


# django-minio-storage

Use [minio](https://minio.io) for django static and media file storage.

Minio is accessed through the Amazon S3 API, so existing django file
storage adapters for S3 should work, but in practice they are hard to
configure. This project uses the minio python client instead. Inspiration has
been drawn from `django-s3-storage` and `django-storages`.

It is tested on python 3 and django 1.8 - 1.11, but should be easily
portable to older versions. Python 2.7 is not supported

The goal is to have a thoroughly tested, small codebase that delegates as
much as possible to the minio client.

Versioning is semver compliant.

## Installation

    pip install django-minio-storage

Add `minio_storage` to `INSTALLED_APPS` in your project settings.

The last step is setting `DEFAULT_FILE_STORAGE` to
`"minio_storage.storage.MinioMediaStorage"`, and `STATICFILES_STORAGE` to
`"minio_storage.storage.MinioStaticStorage"`.

## Configuration

The following settings are available:

- `MINIO_STORAGE_ENDPOINT`: the access url for the service (for example
    `minio.example.org:9000` (note that there is no scheme)).
- `MINIO_STORAGE_ACCESS_KEY` and `MINIO_STORAGE_SECRET_KEY` (mandatory)
- `MINIO_STORAGE_USE_HTTPS`: whether to use TLS or not (default: `True`)
- `MINIO_STORAGE_MEDIA_BUCKET_NAME`: the bucket that will act as `MEDIA` folder
- `MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET`: whether to create the bucket if it
does not already exist (default: `False`)
- `MINIO_STORAGE_STATIC_BUCKET_NAME`: the bucket that will act as `STATIC` folder
- `MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET`: whether to create the bucket if it
does not already exist (default: `False`)

- `MINIO_PARTIAL_URL`: by default a `MINIO_STORAGE_ENDPOINT` is used as a base for file URLs.
However when deployed in docker cluster, it is desired to return only the path and combine with `MINIO_PARTIAL_URL_BASE`
 (default: `False`)
- `MINIO_PARTIAL_URL_BASE`: base for the file's URL. It must be a valid URI without trailing slash at the end,
e.g. 'http://example.com' or 'http://localhost:9000'

- `MINIO_STORAGE_MEDIA_USE_PRESIGNED`: Determines if the media file URLs should be pre-signed (default: `False`)
- `MINIO_STORAGE_STATIC_USE_PRESIGNED`: Determines if the static file URLs should be pre-signed (default: `False`)
By default set to False.

## Short Example
```
STATIC_URL = '/static/'
STATIC_ROOT = './static_files/'

DEFAULT_FILE_STORAGE = "minio_storage.storage.MinioMediaStorage"
STATICFILES_STORAGE = "minio_storage.storage.MinioStaticStorage"
MINIO_STORAGE_ENDPOINT = 'minio:9000'
MINIO_STORAGE_ACCESS_KEY = 'KBP6WXGPS387090EZMG8'
MINIO_STORAGE_SECRET_KEY = 'DRjFXylyfMqn2zilAr33xORhaYz5r9e8r37XPz3A'
MINIO_STORAGE_USE_HTTPS = False
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'local-media'
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
MINIO_STORAGE_STATIC_BUCKET_NAME = 'local-static'
MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET = True

MINIO_PARTIAL_URL = True
MINIO_PARTIAL_URL_BASE = 'http://localhost:9000'
```

## Logging

The library defines a logger with the name 'minio_storage' that you can add to
your django logging configuration.

## Tests

Test coverage is and should remain 100%. The library is very small and a minio
server can be very easily brought up with docker, so there is no reason to use
mocking most of the time, the tests should run directly against a real minio
instance.

To run the tests you need to have minio running locally with some specific
settings, you can start it using docker-compose:

    docker-compose up -d

Use tox to run the tests for all environments in tox.ini:

    tox

Or just run tests for some of them

    tox -e py35-django110,py35-django111

## License

Licensed under either of

 * Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE)
   or http://www.apache.org/licenses/LICENSE-2.0)
 * MIT license ([LICENSE-MIT](LICENSE-MIT)
   or http://opensource.org/licenses/MIT)

at your option.

### Contribution

Unless you explicitly state otherwise, any contribution intentionally submitted
for inclusion in the work by you, as defined in the Apache-2.0 license, shall be
dual licensed as above, without any additional terms or conditions.

## Contributors

- Belek Abylov
- Tom Houlé
- @yml
- Thomas Frössman
