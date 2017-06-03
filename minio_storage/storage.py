from __future__ import unicode_literals

import datetime
import mimetypes
from logging import getLogger
from urllib.parse import urlparse

import minio
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from minio.error import NoSuchBucket, NoSuchKey, ResponseError

from .files import ReadOnlySpooledTemporaryFile

logger = getLogger("minio_storage")


@deconstructible
class MinioStorage(Storage):
    """An implementation of Django's file storage using the minio client.

    The implementation should comply with
    https://docs.djangoproject.com/en/dev/ref/files/storage/.

    """
    file_class = ReadOnlySpooledTemporaryFile

    def __init__(self, minio_client, bucket_name, *,
                 base_url=None, file_class=None,
                 auto_create_bucket=False, presign_urls=False,
                 **kwargs):
        self.client = minio_client
        self.bucket_name = bucket_name
        self.base_url = base_url

        if file_class is not None:
            self.file_class = file_class
        self.auto_create_bucket = auto_create_bucket

        self.presign_urls = presign_urls

        if auto_create_bucket and not self.client.bucket_exists(
                self.bucket_name):
            self.client.make_bucket(self.bucket_name)
        elif not self.client.bucket_exists(self.bucket_name):
            raise IOError("The bucket {} does not exist".format(bucket_name))
        super(MinioStorage, self).__init__()

    def _sanitize_path(self, name):
        return name.lstrip("./")

    def _examine_file(self, name, content):
        """Examines a file and produces information necessary for upload.

        Returns a tuple of the form (content_size, content_type,
        sanitized_name)

        """
        content_size = content.size
        content_type = mimetypes.guess_type(name, strict=False)
        content_type = content_type[0] or "application/octet-stream"
        sane_name = self._sanitize_path(name)
        return (content_size, content_type, sane_name)

    def _open(self, name, mode="rb"):
        f = self.file_class(name, mode, self)
        return f

    def _save(self, name, content):
        # (str, bytes) -> str
        try:
            if hasattr(content, 'seek') and callable(content.seek):
                content.seek(0)
            content_size, content_type, sane_name = self._examine_file(
                name, content)
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
            self.client.stat_object(
                self.bucket_name, self._sanitize_path(name))
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

        # TODO: no need to call presign unless it's used
        url = self.client.presigned_get_object(self.bucket_name, name)

        parsed_url = urlparse(url)

        if self.base_url is not None and self.presign_urls:
            url = '{0}{1}?{2}{3}{4}'.format(
                self.base_url, parsed_url.path, parsed_url.params,
                parsed_url.query, parsed_url.fragment)

        if not self.presign_urls:
            if self.base_url is not None:
                url = '{}{}'.format(self.base_url, parsed_url.path)
            else:
                url = '{}://{}{}'.format(parsed_url.scheme,
                                         parsed_url.netloc, parsed_url.path)

        return url

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


_NoValue = object()


def get_setting(name, default=_NoValue, ):
    result = getattr(settings, name, default)
    if result is _NoValue:
        print("Attr {} : {}".format(name, getattr(settings, name, default)))
        raise ImproperlyConfigured
    else:
        return result


def create_minio_client_from_settings():
    endpoint = get_setting("MINIO_STORAGE_ENDPOINT")
    access_key = get_setting("MINIO_STORAGE_ACCESS_KEY")
    secret_key = get_setting("MINIO_STORAGE_SECRET_KEY")
    secure = get_setting("MINIO_STORAGE_USE_HTTPS", True)
    client = minio.Minio(endpoint,
                         access_key=access_key,
                         secret_key=secret_key,
                         secure=secure)
    return client


def get_base_url_from_settings():
    partial_url = get_setting("MINIO_PARTIAL_URL", False)
    partial_url_base = get_setting("MINIO_PARTIAL_URL_BASE", None)

    if partial_url and not partial_url_base:
        raise NotImplementedError(
            'MINIO_PARTIAL_URL_BASE must be provided '
            'when MINIO_PARTIAL_URL is set to True')
    return partial_url_base


@deconstructible
class MinioMediaStorage(MinioStorage):
    def __init__(self):
        client = create_minio_client_from_settings()
        bucket_name = get_setting("MINIO_STORAGE_MEDIA_BUCKET_NAME")
        base_url = get_base_url_from_settings()
        auto_create_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET", False)
        presign_urls = get_setting(
            'MINIO_STORAGE_MEDIA_USE_PRESIGNED', False)

        super(MinioMediaStorage, self).__init__(
            client, bucket_name,
            auto_create_bucket=auto_create_bucket,
            base_url=base_url,
            presign_urls=presign_urls)


@deconstructible
class MinioStaticStorage(MinioStorage):
    def __init__(self):
        client = create_minio_client_from_settings()
        base_url = get_base_url_from_settings()
        bucket_name = get_setting("MINIO_STORAGE_STATIC_BUCKET_NAME")
        auto_create_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET", False)
        presign_urls = get_setting('MINIO_STORAGE_STATIC_USE_PRESIGNED', False)

        super(MinioStaticStorage, self).__init__(
            client, bucket_name,
            auto_create_bucket=auto_create_bucket,
            base_url=base_url,
            presign_urls=presign_urls)
