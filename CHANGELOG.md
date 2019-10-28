--- NEXT


### 0.3.4

- fixed resource leak where one extra file was opened per file and never closed: https://github.com/py-pa/django-minio-storage/commit/1532e34c7dcecbc2cf3ca0805d6fbf42b57c25ba


### 0.3.3

- reworked management commands and added tests.

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



### 0.3.2

- GET_ONLY is now the default bucket policy
- Added thedjango  mangement commands to the package


### 0.3.1

Changes:

- dropped python 2 support, 3.6+ is now required
- dropped support for django earlier than 1.11
- MINIO_STORAGE_AUTO_CREATE_..._POLICY now has more options (see Policy enum)
- MINIO_STORAGE_AUTO_CREATE_..._POLICY now defaults to GET_ONLY

New feautures:

- django management commands minio_bucket and minio_bucket_policy
- implement Storage.listdir(): https://github.com/py-pa/django-minio-storage/commit/9300d3d0b819672dbae788155258ff499788691c
- add max_age to Storage.url(): https://github.com/py-pa/django-minio-storage/commit/5084b954ad0ba0afad340a8d1010ccd2e491a30c

Fixes:

- urlquote object name when using BASE_URL setting: https://github.com/py-pa/django-minio-storage/commit/960961932bcef8c17fbb774f0ef5fa3022af15a2


## 0.2.2 



