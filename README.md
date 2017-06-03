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

# documentation

See [docs/](docs/index.md)


