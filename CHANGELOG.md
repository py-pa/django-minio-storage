Simple list of user facing changes to keep track of major changes since last release.


--- NEXT

Pending changes/TODO

- Maybe require minio-py 5.0 or later (havent looked at whats actually changed)
- Figure out if the current set of policy presets are suitable.

Changes:

- dropped python 2 support, 3.6+ is now required
- dropped support for django earlier than 1.11
- MINIO_STORAGE_AUTO_CREATE_..._POLICY now has more options (see Policy enum)
- MINIO_STORAGE_AUTO_CREATE_..._POLICY now defaults to GET_ONLY


Fixes:

- urlquote object name when using BASE_URL setting: https://github.com/py-pa/django-minio-storage/commit/960961932bcef8c17fbb774f0ef5fa3022af15a2

- implement Storage.listdir(): https://github.com/py-pa/django-minio-storage/commit/9300d3d0b819672dbae788155258ff499788691c
- add max_age to Storage.url(): https://github.com/py-pa/django-minio-storage/commit/5084b954ad0ba0afad340a8d1010ccd2e491a30c

--- 0.2.2 


