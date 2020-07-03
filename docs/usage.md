## Installation

```sh
pip install django-minio-storage
```

Add `minio_storage` to `INSTALLED_APPS` in your project settings.

The last step is setting `DEFAULT_FILE_STORAGE` to
`"minio_storage.storage.MinioMediaStorage"`, and `STATICFILES_STORAGE` to
`"minio_storage.storage.MinioStaticStorage"`.

## Django settings Configuration

The following settings are available:

- `MINIO_STORAGE_ENDPOINT`: the access URL for the service (for example
  `minio.example.org:9000` (note that there is no scheme)).

- `MINIO_STORAGE_ACCESS_KEY` and `MINIO_STORAGE_SECRET_KEY` (mandatory)

- `MINIO_STORAGE_USE_HTTPS`: whether to use TLS or not (default: `True`). This
  affect both how how Django internally communicates with the Minio server AND
  controls if the generated the storage object URLs uses `http://` or
  `https://` schemes.

- `MINIO_STORAGE_MEDIA_BUCKET_NAME`: the bucket that will act as `MEDIA` folder

- `MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET`: whether to create the bucket if it
  does not already exist (default: `False`)

- `MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS`: whether to ignore media bucket 
  creation and policy.  
  (default: `False`)

- `MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY`: sets the buckets public policy
  right after it's been created by `MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET`.
  Valid values are: `GET_ONLY`, `READ_ONLY`, `WRITE_ONLY`, `READ_WRITE` and
  `NONE`. (default: `GET_ONLY`)
  
- `MINIO_STORAGE_MEDIA_OBJECT_METADATA`: set default additional metadata for
  every object persisted during save operations. The value is a dict with
  string keys and values, example: `{"Cache-Control": "max-age=1000"}`.
  (default: `None`)

- `MINIO_STORAGE_STATIC_BUCKET_NAME`: the bucket that will act as `STATIC`
  folder

- `MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET`: whether to create the bucket if it
  does not already exist (default: `False`)


- `MINIO_STORAGE_ASSUME_STATIC_BUCKET_EXISTS`: whether to ignore the static bucket 
  creation and policy.  
  (default: `False`)

- `MINIO_STORAGE_AUTO_CREATE_STATIC_POLICY`: sets the buckets public policy
  right after it's been created by `MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET`.
  Valid values are: `GET_ONLY`, `READ_ONLY`, `WRITE_ONLY`, `READ_WRITE` and
  `NONE`. (default: `GET_ONLY`)
  
- `MINIO_STORAGE_STATIC_OBJECT_METADATA`: set default additional metadata for
  every object persisted during save operations. The value is a dict with
  string keys and values, example: `{"Cache-Control": "max-age=1000"}`.
  (default: `None`)

- `MINIO_STORAGE_MEDIA_URL`: the base URL for generating urls to objects from
  `MinioMediaStorage`. When not specified or set to `None` it's value will be
  combined from `MINIO_STORAGE_ENDPOINT` and `MINIO_STORAGE_MEDIA_BUCKET_NAME`.
  `MINIO_STORAGE_MEDIA_URL` should contain the full base url including the
  bucket name without a trailing slash. Normally, this should not have to be
  set, but may be useful when the storage and end user must access the server
  from different endpoints.

- `MINIO_STORAGE_STATIC_URL`: the base URL for generating URLs to objects from
  `MinioStaticStorage`. When not specified or set to `None` it's value will be
  combined from `MINIO_STORAGE_ENDPOINT` and
  `MINIO_STORAGE_STATIC_BUCKET_NAME`. `MINIO_STORAGE_STATIC_URL` should contain
  the full base url including the bucket name without a trailing slash.
  Normally, this should not have to be set, but may be useful when the storage
  and end user must access the server from different endpoints.

- `MINIO_STORAGE_MEDIA_BACKUP_BUCKET`: Bucket to be used to store deleted files.
  The bucket **has to exists**, the storage will not try to create it.
  Required if `MINIO_STORAGE_MEDIA_BACKUP_FORMAT` is set.

- `MINIO_STORAGE_MEDIA_BACKUP_FORMAT`: Path to be used to store deleted files,
  the path can contain Python's `strftime` substitutes, such as `%H`, `%c` and
  others. The object name will be appended to the resulting path, without
  actually forcing another `/` at the end, so if you set this setting to
  `backup-%Y-%m_` then the resulting object name will be (e.g.)
  `backup-2018-07_my_object.data`. If you want to store the objects inside
  folders, make sure to finish this setting with a forward slash.
  Required if `MINIO_STORAGE_MEDIA_BACKUP_BUCKET` is set.

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
MINIO_STORAGE_MEDIA_OBJECT_METADATA = {"Cache-Control": "max-age=1000"}
MINIO_STORAGE_MEDIA_BUCKET_NAME = 'local-media'
MINIO_STORAGE_MEDIA_BACKUP_BUCKET = 'Recycle Bin'
MINIO_STORAGE_MEDIA_BACKUP_FORMAT = '%c/'
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
MINIO_STORAGE_STATIC_BUCKET_NAME = 'local-static'
MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET = True

# These settings should generally not be used:
# MINIO_STORAGE_MEDIA_URL = 'http://localhost:9000/local-media'
# MINIO_STORAGE_STATIC_URL = 'http://localhost:9000/local-static'
```

## Logging

The library defines a logger with the name `minio_storage` that you can add to
your Django logging configuration.
