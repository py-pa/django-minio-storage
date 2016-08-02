# django-minio-storage

[![Build Status](https://travis-ci.org/tomhoule/django-minio-storage.svg?branch=master)](https://travis-ci.org/tomhoule/django-minio-storage)

Use [minio](https://minio.io) for django static and media file storage.

Minio is accessed through the Amazon S3 API, so existing django file
storage adapters for S3 should work, but in practice they are hard to
configure. This project uses the minio python client instead. Inspiration has
been drawn from `django-s3-storage` and `django-storages`.

It is tested on python 3 and django 1.9 at the moment, but should be easily
portable to older versions.

The goal is to have a thoroughly tested, small codebase that delegates as
much as possible to the minio client.

Versioning is semver compliant.

## Status

This library is still a work in progress and not suitable for production
use yet. Contributions and ideas are welcome (I mean it).

See the issues to see what needs to be done for a 1.0 release to happen.

## Installation

    pip install django-minio-storage

Add `minio_storage` to `INSTALLED_APPS` in your project settings.

The last step is setting `DEFAULT_FILE_STORAGE` to
`"minio_storage.storage.MinioMediaStorage"`, and `STATICFILES_STORAGE` to
`"minio_storage.storages.MinioStaticStorage"`.

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

## Logging

The library defines a logger with the name 'minio_storage' that you can add to
your django logging configuration.

## Tests

Test coverage is and should remain 100%. The library is very small and a minio
server can be very easily brought up with docker, so there is no reason to use
mocking most of the time, the tests should run directly against a real minio
instance.

To run the tests, you need docker and docker compose, then it is as simple as:

    docker-compose run django ./run_tests.sh

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
