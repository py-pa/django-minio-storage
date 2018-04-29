# encoding: utf-8
from __future__ import unicode_literals

import datetime
import json
import mimetypes
from logging import getLogger
from time import mktime

import minio
import minio.error as merr
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from minio.helpers import get_target_url

from .errors import minio_error
from .files import ReadOnlySpooledTemporaryFile

try:
    from urllib.parse import urlparse
except ImportError:  # Python 2.7 compatibility
    from urlparse import urlparse


logger = getLogger("minio_storage")


@deconstructible
class MinioStorage(Storage):
    """An implementation of Django's file storage using the minio client.

    The implementation should comply with
    https://docs.djangoproject.com/en/dev/ref/files/storage/.

    """
    file_class = ReadOnlySpooledTemporaryFile

    def __init__(self, minio_client, bucket_name,
                 base_url=None, file_class=None,
                 auto_create_bucket=False, presign_urls=False,
                 auto_create_policy=False,
                 *args, **kwargs):
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

            if auto_create_policy:
                self.client.set_bucket_policy(
                    self.bucket_name,
                    self._policy("READ_ONLY")
                )

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
        try:
            f = self.file_class(name, mode, self)
        except merr.MinioError as e:
            raise minio_error(
                "File {} could not be saved: {}".format(name, str(e)), e)
        return f

    def _policy(self, type):
        """
        Dictionary containing basic AWS Policies in JSON format
        Policies: READ_ONLY, WRITE_ONLY, READ_WRITE
        """
        Policy = {
            "READ_ONLY": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "s3:GetBucketLocation",
                        "Resource": "arn:aws:s3:::%s" % (self.bucket_name)
                    },
                    {
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "s3:ListBucket",
                        "Resource": "arn:aws:s3:::%s" % (self.bucket_name)
                    },
                    {
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "s3:GetObject",
                        "Resource": "arn:aws:s3:::%s/*" % (self.bucket_name)
                    }
                ]
            },
            "WRITE_ONLY": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "s3:GetBucketLocation",
                        "Resource": "arn:aws:s3:::%s" % (self.bucket_name)
                    },
                    {
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "s3:ListBucketMultipartUploads",
                        "Resource": "arn:aws:s3:::%s" % (self.bucket_name)
                    },
                    {
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": [
                            "s3:ListMultipartUploadParts",
                            "s3:AbortMultipartUpload",
                            "s3:DeleteObject",
                            "s3:PutObject"
                        ],
                        "Resource": "arn:aws:s3:::%s/*" % (self.bucket_name)
                    }
                ]
            },
            "READ_WRITE": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": ["s3:GetBucketLocation"],
                        "Sid": "",
                        "Resource": ["arn:aws:s3:::%s" % (self.bucket_name)],
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"}
                    },
                    {
                        "Action": ["s3:ListBucket"],
                        "Sid": "",
                        "Resource": ["arn:aws:s3:::%s" % (self.bucket_name)],
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"}
                    },
                    {
                        "Action": ["s3:ListBucketMultipartUploads"],
                        "Sid": "",
                        "Resource": ["arn:aws:s3:::%s" % (self.bucket_name)],
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"}
                    },
                    {
                        "Action": [
                            "s3:ListMultipartUploadParts",
                            "s3:GetObject",
                            "s3:AbortMultipartUpload",
                            "s3:DeleteObject",
                            "s3:PutObject"
                        ],
                        "Sid": "",
                        "Resource": ["arn:aws:s3:::%s/*" % (self.bucket_name)],
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"}
                    }
                ]
            }
        }

        return json.dumps(Policy[type])

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
        except merr.ResponseError as error:
            raise minio_error("File {} could not be saved".format(name), error)

    def delete(self, name):
        # type: (str) -> None
        try:
            self.client.remove_object(self.bucket_name, name)
        except merr.ResponseError as error:
            raise minio_error("Could not remove file {}".format(name), error)

    def exists(self, name):
        # type: (str) -> bool
        try:
            self.client.stat_object(
                self.bucket_name, self._sanitize_path(name))
            return True
        except merr.ResponseError as error:
            # TODO - deprecate
            if error.code == "NoSuchKey":
                return False
            else:
                raise minio_error("Could not stat file {}".format(name), error)
        except merr.NoSuchKey as error:
            return False
        except merr.NoSuchBucket:
            raise
        except Exception as error:
            logger.error(error)

    def listdir(self, prefix):
        try:
            # TODO: break the path
            objects = self.client.list_objects(self.bucket_name, prefix)
            return objects
        except merr.NoSuchBucket:
            raise
        except merr.ResponseError as error:
            raise minio_error(
                "Could not list directory {}".format(prefix), error)

    def size(self, name):
        # type: (str) -> int
        try:
            info = self.client.stat_object(self.bucket_name, name)
            return info.size
        except merr.ResponseError as error:
            raise minio_error(
                "Could not access file size for {}".format(name), error)

    def url(self, name):
        # type: (str) -> str

        # NOTE: Here be dragons, when a external base_url is used the code
        # below is both using "internal" minio clint APIs and somewhat
        # subverting how minio/S3 expects urls to be generated in the first
        # place.
        if self.presign_urls:
            url = self.client.presigned_get_object(self.bucket_name, name)
            if self.base_url is not None:
                parsed_url = urlparse(url)
                path = parsed_url.path.split(self.bucket_name, 1)[1]
                url = '{0}{1}?{2}{3}{4}'.format(
                    self.base_url, path, parsed_url.params,
                    parsed_url.query, parsed_url.fragment)

        else:
            if self.base_url is not None:
                def strip_beg(path):
                    while path.startswith('/'):
                        path = path[1:]
                    return path

                def strip_end(path):
                    while path.endswith('/'):
                        path = path[:-1]
                    return path
                url = "{}/{}".format(strip_end(self.base_url),
                                     strip_beg(name))
            else:
                url = get_target_url(self.client._endpoint_url,
                                     bucket_name=self.bucket_name,
                                     object_name=name,
                                     # bucket_region=region,
                                     )
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
            return datetime.datetime.fromtimestamp(mktime(info.last_modified))
        except merr.ResponseError as error:
            raise minio_error(
                "Could not access modification time for file {}"
                .format(name), error)


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


@deconstructible
class MinioMediaStorage(MinioStorage):
    def __init__(self):
        client = create_minio_client_from_settings()
        bucket_name = get_setting("MINIO_STORAGE_MEDIA_BUCKET_NAME")
        base_url = get_setting("MINIO_STORAGE_MEDIA_URL", None)
        auto_create_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET", False)
        auto_create_policy = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY", False)
        presign_urls = get_setting(
            'MINIO_STORAGE_MEDIA_USE_PRESIGNED', False)

        super(MinioMediaStorage, self).__init__(
            client, bucket_name,
            auto_create_bucket=auto_create_bucket,
            auto_create_policy=auto_create_policy,
            base_url=base_url,
            presign_urls=presign_urls)


@deconstructible
class MinioStaticStorage(MinioStorage):
    def __init__(self):
        client = create_minio_client_from_settings()
        base_url = get_setting("MINIO_STORAGE_STATIC_URL", None)
        bucket_name = get_setting("MINIO_STORAGE_STATIC_BUCKET_NAME")
        auto_create_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET", False)
        auto_create_policy = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_STATIC_POLICY", False)

        presign_urls = get_setting('MINIO_STORAGE_STATIC_USE_PRESIGNED', False)

        super(MinioStaticStorage, self).__init__(
            client, bucket_name,
            auto_create_bucket=auto_create_bucket,
            auto_create_policy=auto_create_policy,
            base_url=base_url,
            presign_urls=presign_urls)
