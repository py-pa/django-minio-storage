## Installation

```sh
pip install django-minio-storage-py-pa
```

Add `minio_storage` to `INSTALLED_APPS` in your project settings.

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

- `MINIO_STORAGE_STATIC_BUCKET_NAME`: the bucket that will act as `STATIC`
  folder

- `MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET`: whether to create the bucket if it
  does not already exist (default: `False`)

- `MINIO_STORAGE_MEDIA_URL`: the base URL for generating urls to objects from
  `MinioMediaStorage`. When not specified or set to `None` it's value will be
  combined from `MINIO_STORAGE_ENDPOINT` and `MINIO_STORAGE_MEDIA_BUCKET_NAME`.
  `MINIO_STORAGE_MEDIA_URL` should contain the full base url including the
  bucket name without a trailing slash. Please not that when using presigned
  URLs, the URL itself is a part of the calculated signature so be careful with
  how `MINIO_STORAGE_MEDIA_URL` is used, normally it doest have to be set at
  all.

- `MINIO_STORAGE_STATIC_URL`: the base URL for generating urls to objects from
  `MinioStaticStorage`. When not specified or set to `None` it's value will be
  combined from `MINIO_STORAGE_ENDPOINT` and
  `MINIO_STORAGE_STATIC_BUCKET_NAME`. `MINIO_STORAGE_STATIC_URL` should contain
  the full base url including the bucket name without a trailing slash. Please
  not that when using presigned URLs, the URL itself is a part of the
  calculated signature so be careful with how `MINIO_STORAGE_STATIC_URL` is
  used, normally it doest have to be set at all.

- `MINIO_STORAGE_MEDIA_USE_PRESIGNED`: Determines if the media file URLs should
  be pre-signed (default: `False`)

- `MINIO_STORAGE_STATIC_USE_PRESIGNED`: Determines if the static file URLs
  should be pre-signed (default: `False`) By default set to False.

## Short Example

```py
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

MINIO_MEDIA_URL = 'http://localhost:9000/local-media'
MINIO_STATIC_URL = 'http://localhost:9000/local-static'
```

## Logging

The library defines a logger with the name `minio_storage` that you can add to
your django logging configuration.
