from __future__ import unicode_literals

import datetime
import mimetypes
from logging import getLogger
try:
    from urllib.parse import urlparse
except ImportError:
     from urlparse import urlparse

import minio
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from minio.error import NoSuchBucket, NoSuchKey, ResponseError
from minio.policy import Policy

from minio.helpers import get_target_url

logger = getLogger("minio_storage")


def get_setting(name, default=None):
        result = getattr(settings, name, default)
        if result is None:
            print("Attr {} : {}".format(name, getattr(settings, name, default)))
            raise ImproperlyConfigured
        else:
            return result


@deconstructible
class MinioStorage(Storage):
    """
    An implementation of Django's file storage using the minio client.
    The implementation should comply with https://docs.djangoproject.com/en/dev/ref/files/storage/.
    """

    def __init__(self):
        self.endpoint = get_setting("MINIO_STORAGE_ENDPOINT")
        self.access_key = get_setting("MINIO_STORAGE_ACCESS_KEY")
        self.secret_key = get_setting("MINIO_STORAGE_SECRET_KEY")
        self.secure = get_setting("MINIO_STORAGE_USE_HTTPS", True)

        self.partial_url = get_setting("MINIO_PARTIAL_URL", False)
        self.partial_url_base = get_setting("MINIO_PARTIAL_URL_BASE", None)

        if self.partial_url and not self.partial_url_base:
            raise NotImplementedError('MINIO_PARTIAL_URL_BASE must be provided '
                                      'when MINIO_PARTIAL_URL is set to True')

        self.client = minio.Minio(self.endpoint,
                                  access_key=self.access_key,
                                  secret_key=self.secret_key,
                                  secure=self.secure)

        super(MinioStorage, self).__init__()

    def _sanitize_path(self, name):
        return name.lstrip("./")

    def _examine_file(self, name, content):
        """
        Examines a file and produces information necessary for upload.

        Returns a tuple of the form (content_size, content_type, sanitized_name)
        """
        content_size = content.size
        content_type = mimetypes.guess_type(name, strict=False)
        content_type = content_type[0] or "application/octet-stream"
        sane_name = self._sanitize_path(name)
        return (content_size, content_type, sane_name)

    def _open(self, name, mode="rb"):
        if mode.find("w") > -1:
            raise NotImplementedError("Minio storage cannot write to file")
        try:
            return self.client.get_object(self.bucket_name, name)
        except ResponseError as error:
            logger.warn(error)
            raise IOError("File {} does not exist".format(name))

    def _save(self, name, content):
        # (str, bytes) -> str
        try:
            content_size, content_type, sane_name = self._examine_file(name, content)
            self.client.put_object(self.bucket_name,
                                   sane_name,
                                   content,
                                   content_size,
                                   content_type)
            return sane_name
        except ResponseError as error:
            logger.warn(error)
            raise IOError("File {} could not be saved".format(name))

    def delete(self, name):
        # type: (str) -> None
        try:
            self.client.remove_object(self.bucket_name, name)
        except ResponseError as error:
            logger.warn("Object deletion failed")
            logger.warn(error)
            raise IOError("Could not remove file {}".format(name))

    def exists(self, name):
        # type: (str) -> bool
        try:
            self.client.stat_object(self.bucket_name, self._sanitize_path(name))
            return True
        except ResponseError as error:
            # TODO - deprecate
            if error.code == "NoSuchKey":
                return False
            else:
                logger.warn(error)
                raise IOError("Could not stat file {}".format(name))
        except NoSuchKey as error:
            return False
        # Temporary - due to https://github.com/minio/minio-py/issues/514
        except NoSuchBucket as error:
            return False
        except Exception as error:
            logger.warn(error)
            raise IOError("Could not stat file {}".format(name))

    def listdir(self, prefix):
        try:
            # TODO: break the path
            objects = self.client.list_objects(self.bucket_name, prefix)
            return objects
        except ResponseError as error:
            logger.warn(error)
            raise IOError("Could not list directory {}".format(prefix))

    def size(self, name):
        # type: (str) -> int
        try:
            info = self.client.stat_object(self.bucket_name, name)
            return info.size
        except ResponseError as error:
            logger.warn(error)
            raise IOError("Could not access file size for {}".format(name))

    def url(self, name):
        # type: (str) -> str
        if self.exists(name):
            url = self.client.presigned_get_object(self.bucket_name, name)

            parsed_url = urlparse(url)

            if self.partial_url and self.presigned:
                url = '{0}{1}?{2}{3}{4}'.format(self.partial_url_base, parsed_url.path, parsed_url.params,
                                                parsed_url.query, parsed_url.fragment)

            if not self.presigned:
                if self.partial_url:
                    url = '{}{}'.format(self.partial_url_base, parsed_url.path)
                else:
                    url = '{}://{}{}'.format(parsed_url.scheme, parsed_url.netloc, parsed_url.path)

            return url
        else:
            raise IOError("This file does not exist")

    def accessed_time(self, name):
        # type: (str) -> datetime.datetime
        """
        Not available via the S3 API
        """
        return self.modified_time(name)

    def created_time(self, name):
        # type: (str) -> datetime.datetime
        """
        Not available via the S3 API
        """
        return self.modified_time(name)

    def modified_time(self, name):
        # type: (str) -> datetime.datetime
        try:
            info = self.client.stat_object(self.bucket_name, name)
            return datetime.datetime.fromtimestamp(info.last_modified)
        except ResponseError as error:
            logger.warn(error)
            raise IOError(
                "Could not access modification time for file {}".format(name))


@deconstructible
class MinioMediaStorage(MinioStorage):
    def __init__(self):
        super(MinioMediaStorage, self).__init__()
        self.bucket_name = get_setting("MINIO_STORAGE_MEDIA_BUCKET_NAME")
        self.auto_create_media_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET", False)
        self.presigned = get_setting('MINIO_STORAGE_MEDIA_USE_PRESIGNED', False)

        if self.auto_create_media_bucket and not self.client.bucket_exists(
                                                 self.bucket_name):
            self.client.make_bucket(self.bucket_name)
            self.client.set_bucket_policy(self.bucket_name, '*', Policy.READ_ONLY)
        elif not self.client.bucket_exists(self.bucket_name):
            raise IOError("The media bucket does not exist")


@deconstructible
class MinioStaticStorage(MinioStorage):
    def __init__(self):
        super(MinioStaticStorage, self).__init__()
        self.bucket_name = get_setting("MINIO_STORAGE_STATIC_BUCKET_NAME")
        self.auto_create_static_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET", False)
        self.presigned = get_setting('MINIO_STORAGE_STATIC_USE_PRESIGNED', False)

        if self.auto_create_static_bucket and not self.client.bucket_exists(
                                                 self.bucket_name):
            self.client.make_bucket(self.bucket_name)
            self.client.set_bucket_policy(self.bucket_name, '*', Policy.READ_ONLY)
        elif not self.client.bucket_exists(self.bucket_name):
            raise IOError("The static bucket does not exist")
