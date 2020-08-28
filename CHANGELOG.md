## 0.3.9

The minio client is now deconstructable by Django, fixes migrations.

## 0.3.8

Improved presigned urls with non standard base urls

## 0.3.7

Removed accidentally left over debug print from previous release

## 0.3.6

### support adding default meta data

Also new settings: MINIO_STORAGE_MEDIA_OBJECT_METADATA and
MINIO_STORAGE_STATIC_OBJECT_METADATA

example:

```py
MINIO_STORAGE_MEDIA_OBJECT_METADATA  = {"Cache-Control": "max-age=1000"}
```

### fix issue with directory listing names

Minio has changed in the last months to be more picky about path names so we
now enure that we don't create path prefixes with a // suffix.


## 0.3.5

#### Add support for skipping bucket existst/policy check on start up
https://github.com/py-pa/django-minio-storage/commit/7086f125ed74b157240bae10c589ce785ca93bbf

Added settings MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS and
MINIO_STORAGE_ASSUME_STATIC_BUCKET_EXISTS

## 0.3.4

#### • fixed resource leak where one extra file was opened per file and never closed
https://github.com/py-pa/django-minio-storage/commit/1532e34c7dcecbc2cf3ca0805d6fbf42b57c25ba
  
There leaked file descriptors were only freed by the gargabe collector before
this fix so if you have farily tight loop that does something to a lot of files
while not generating a lot of garbage to trigger the gc.


## 0.3.3

#### • reworked management commands and added tests.

```
$ python manage.py minio
usage: minio  [-h] [--class CLASS] [--bucket BUCKET] [--version]
              [-v {0,1,2,3}] [--settings SETTINGS] [--pythonpath PYTHONPATH]
              [--traceback] [--no-color] [--force-color]
              {check,create,delete,ls,policy} ...
   ...
minio:
  --class CLASS         Storage class to modify (media/static are short names
                        for default classes)
  --bucket BUCKET       bucket name (default: storage defined bucket if not
                        set)

subcommands:
  valid subcommands

  {check,create,delete,ls,policy}
    check               check bucket
    create              make bucket
    delete              remove an empty bucket
    ls                  list bucket objects or buckets
    policy              get or set bucket policy
```


## 0.3.2

#### • GET_ONLY is now the default bucket policy


## 0.3.1

### Changes

#### • dropped python 2 support, 3.6+ is now required

#### • dropped support for django earlier than 1.11

#### • policy settings default values changed

- MINIO_STORAGE_AUTO_CREATE_..._POLICY now has more options (see Policy enum)
- MINIO_STORAGE_AUTO_CREATE_..._POLICY now defaults to GET_ONLY

### New feautures

#### • new django management commands

- minio_bucket
- minio_bucket_policy
#### • implement Storage.listdir(): 

https://github.com/py-pa/django-minio-storage/commit/9300d3d0b819672dbae788155258ff499788691c

#### • add max_age to Storage.url()

https://github.com/py-pa/django-minio-storage/commit/5084b954ad0ba0afad340a8d1010ccd2e491a30c

### Fixes

#### • urlquote object name when using BASE_URL setting

https://github.com/py-pa/django-minio-storage/commit/960961932bcef8c17fbb774f0ef5fa3022af15a2


## 0.2.2 



