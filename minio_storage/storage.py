import minio
from minio.error import ResponseError

from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.conf import settings

import mimetypes
import datetime

from logging import getLogger

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
    An implementation of Django’s file storage using the minio client.
    """

    def __init__(self):
        self.endpoint = get_setting("MINIO_STORAGE_ENDPOINT")
        self.access_key = get_setting("MINIO_STORAGE_ACCESS_KEY")
        self.secret_key = get_setting("MINIO_STORAGE_SECRET_KEY")
        self.secure = get_setting("MINIO_STORAGE_USE_HTTPS", True)

        self.client = minio.Minio(self.endpoint,
                                  access_key=self.access_key,
                                  secret_key=self.secret_key,
                                  secure=self.secure)

        super().__init__()

    def _examine_file(self, name, content):
        """
        Examines a file and produces information necessary for upload.

        Returns a tuple of the form (content_size, content_type)
        """
        content_size = content.size
        content_type = mimetypes.guess_type(name, strict=False)
        content_type = content_type[0] or "application/octet-stream"
        return (content_size, content_type)

    def _open(self, name, mode="rb"):
        if mode.find("w") > -1:
            raise NotImplementedError("Minio storage cannot write to file")
        try:
            return self.client.get_object(self.bucket_name, name)
        except ResponseError as error:
            logger.warn(error)
            raise IOError("File {} does not exist".format(name))

    def _save(self, name, content):
        try:
            content_size, content_type = self._examine_file(name, content)
            self.client.put_object(self.bucket_name,
                                   name,
                                   content,
                                   content_size,
                                   content_type)
            return name
        except ResponseError as error:
            logger.warn(error)
            raise IOError("File {} could not be saved".format(name))

    def delete(self, name):
        try:
            self.client.remove_object(self.bucket_name, name)
        except ResponseError as error:
            logger.warn(error)
            raise IOError("Could not remove file {}".format(name))

    def exists(self, name):
        try:
            self.client.stat_object(self.bucket_name, name)
            return True
        except ResponseError as error:
            if error.code == "NoSuchKey":
                return False
            else:
                logger.warn(error)
                raise IOError("Could not stat file {}".format(name))

    def listdir(self, path):
        try:
            # TODO: break the path
            return self.client.list_objects(self.bucket_name, path)
        except ResponseError as error:
            logger.warn(error)
            raise IOError("Could not list directory {}".format(path))

    def size(self, name):
        try:
            info = self.client.stat_object(self.bucket_name, name)
            return info.size
        except ResponseError as error:
            logger.warn(error)
            raise IOError("Could not access file size for {}".format(name))

    def url(self, name):
        if self.exists(name):
            return self.client.presigned_get_object(self.bucket_name, name)
        else:
            raise IOError("This file does not exist")

    def accessed_time(self, name):
        """
        Not available via the S3 API
        """
        return self.modified_time(name)

    def created_time(self, name):
        """
        Not available via the S3 API
        """
        return self.modified_time(name)

    def modified_time(self, name):
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
        super().__init__()
        self.bucket_name = get_setting("MINIO_STORAGE_MEDIA_BUCKET_NAME")
        # self.static_use_media_bucket = get_setting(
        #     "MINIO_STORAGE_STATIC_USE_MEDIA_BUCKET")
        self.auto_create_media_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET", False)

        if self.auto_create_media_bucket and not self.client.bucket_exists(
                                                 self.bucket_name):
            self.client.make_bucket(self.bucket_name)
        elif not self.client.bucket_exists(self.bucket_name):
            raise IOError("The media bucket does not exist")


@deconstructible
class MinioStaticStorage(MinioStorage):
    def __init__(self):
        super().__init__()
        self.bucket_name = get_setting("MINIO_STORAGE_STATIC_BUCKET_NAME")
        self.auto_create_static_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET", False)

        if self.auto_create_static_bucket and not self.client.bucket_exists(
                                                 self.bucket_name):
            self.client.make_bucket(self.bucket_name)
        elif not self.client.bucket_exists(self.bucket_name):
            raise IOError("The static bucket does not exist")
