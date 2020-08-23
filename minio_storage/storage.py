import datetime
import mimetypes
import posixpath
import typing as T
import urllib
from logging import getLogger
from time import mktime
from urllib.parse import urlsplit, urlunsplit

import minio
import minio.error as merr
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from minio.helpers import get_target_url

from minio_storage.errors import minio_error
from minio_storage.files import ReadOnlySpooledTemporaryFile
from minio_storage.policy import Policy

logger = getLogger("minio_storage")


@deconstructible
class MinioStorage(Storage):
    """An implementation of Django's file storage using the minio client.

    The implementation should comply with
    https://docs.djangoproject.com/en/dev/ref/files/storage/.

    """

    file_class = ReadOnlySpooledTemporaryFile

    def __init__(
        self,
        minio_client: minio.Minio,
        bucket_name: str,
        *,
        base_url: T.Optional[str] = None,
        file_class=None,
        auto_create_bucket: bool = False,
        presign_urls: bool = False,
        auto_create_policy: bool = False,
        policy_type: T.Optional[Policy] = None,
        object_metadata: T.Optional[T.Dict[str, str]] = None,
        backup_format: T.Optional[str] = None,
        backup_bucket: T.Optional[str] = None,
        assume_bucket_exists: bool = False,
        **kwargs,
    ):
        self.client = minio_client
        self.bucket_name = bucket_name
        self.base_url = base_url

        self.backup_format = backup_format
        self.backup_bucket = backup_bucket
        if bool(self.backup_format) != bool(self.backup_bucket):
            raise ImproperlyConfigured(
                "To enable backups, make sure to set both backup format "
                "and backup format"
            )

        if file_class is not None:
            self.file_class = file_class
        self.auto_create_bucket = auto_create_bucket
        self.auto_create_policy = auto_create_policy
        self.assume_bucket_exists = assume_bucket_exists
        self.policy_type = policy_type
        self.presign_urls = presign_urls
        self.object_metadata = object_metadata

        self._init_check()

        # A base_url_client is only necessary when using presign_urls
        if self.presign_urls and self.base_url:
            # Do this after _init_check, so client's bucket region cache will
            # already be populated
            self.base_url_client = self._create_base_url_client(
                self.client, self.bucket_name, self.base_url
            )

        super().__init__()

    def _init_check(self):
        if not self.assume_bucket_exists:
            if self.auto_create_bucket and not self.client.bucket_exists(
                self.bucket_name
            ):
                self.client.make_bucket(self.bucket_name)
                if self.auto_create_policy:
                    policy_type = self.policy_type
                    if policy_type is None:
                        policy_type = Policy.get
                    self.client.set_bucket_policy(
                        self.bucket_name, policy_type.bucket(self.bucket_name)
                    )

            elif not self.client.bucket_exists(self.bucket_name):
                raise OSError(f"The bucket {self.bucket_name} does not exist")

    @staticmethod
    def _create_base_url_client(client: minio.Minio, bucket_name: str, base_url: str):
        """
        Clone a Minio client, using a different endpoint from `base_url`.
        """
        base_url_parts = urlsplit(base_url)

        # Clone from the normal client, but with base_url as the endpoint
        base_url_client = minio.Minio(
            base_url_parts.netloc,
            access_key=client._access_key,
            secret_key=client._secret_key,
            session_token=client._session_token,
            secure=base_url_parts.scheme == "https",
            # The bucket region may be auto-detected by client (via an HTTP
            # request), so don't just use client._region
            region=client._get_bucket_region(bucket_name),
            http_client=client._http,
        )
        if hasattr(client, "_credentials"):
            # Client credentials do not exist prior to minio-py 5.0.7, but
            # they should be reused if possible
            base_url_client._credentials = client._credentials

        return base_url_client

    def _sanitize_path(self, name):
        v = posixpath.normpath(name).replace("\\", "/")
        if v == ".":
            v = ""
        if name.endswith("/") and not v.endswith("/"):
            v += "/"
        return v

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
            f = self.file_class(self._sanitize_path(name), mode, self)
        except merr.MinioError as e:
            raise minio_error("File {} could not be saved: {}".format(name, str(e)), e)
        return f

    def _save(self, name: str, content: bytes) -> str:
        try:
            if hasattr(content, "seek") and callable(content.seek):
                content.seek(0)
            content_size, content_type, sane_name = self._examine_file(name, content)
            self.client.put_object(
                self.bucket_name,
                sane_name,
                content,
                content_size,
                content_type,
                metadata=self.object_metadata,
            )
            return sane_name
        except merr.ResponseError as error:
            raise minio_error(f"File {name} could not be saved", error)

    def delete(self, name: str) -> None:
        if self.backup_format and self.backup_bucket:
            try:
                obj = self.client.get_object(self.bucket_name, name)
            except merr.ResponseError as error:
                raise minio_error(
                    "Could not obtain file {} " "to make a copy of it".format(name),
                    error,
                )

            try:
                content_length = int(obj.getheader("Content-Length"))
            except ValueError as error:
                raise minio_error(f"Could not backup removed file {name}", error)

            # Creates the backup filename
            target_name = "{}{}".format(
                timezone.now().strftime(self.backup_format), name
            )
            try:
                self.client.put_object(
                    self.backup_bucket, target_name, obj, content_length
                )
            except merr.ResponseError as error:
                raise minio_error(
                    "Could not make a copy of file "
                    "{} before removing it".format(name),
                    error,
                )

        try:
            self.client.remove_object(self.bucket_name, name)
        except merr.ResponseError as error:
            raise minio_error(f"Could not remove file {name}", error)

    def exists(self, name: str) -> bool:
        try:
            self.client.stat_object(self.bucket_name, self._sanitize_path(name))
            return True
        except merr.ResponseError as error:
            # TODO - deprecate
            if error.code == "NoSuchKey":
                return False
            else:
                raise minio_error(f"Could not stat file {name}", error)
        except merr.NoSuchKey:
            return False
        except merr.NoSuchBucket:
            raise
        except Exception as error:
            logger.error(error)

    def listdir(self, path: str) -> T.Tuple[T.List, T.List]:
        #  [None, "", "."] is supported to mean the configured root among various
        #  implementations of Storage implementations so we copy that behaviour even if
        #  maybe None should raise an exception instead.
        #
        #  If the path prefix does not match anything full prefix that does exist this
        #  function will just return empty results, this is different from
        #  FileSystemStorage where an invalid directory would raise an OSError.

        if path in [None, "", ".", "/"]:
            path = ""
        else:
            if not path.endswith("/"):
                path += "/"

        dirs: T.List[str] = []
        files: T.List[str] = []
        try:
            objects = self.client.list_objects_v2(self.bucket_name, prefix=path)
            for o in objects:
                p = posixpath.relpath(o.object_name, path)
                if o.is_dir:
                    dirs.append(p)
                else:
                    files.append(p)
            return dirs, files
        except merr.NoSuchBucket:
            raise
        except merr.ResponseError as error:
            raise minio_error(f"Could not list directory {path}", error)

    def size(self, name: str) -> int:
        try:
            info = self.client.stat_object(self.bucket_name, name)
            return info.size
        except merr.ResponseError as error:
            raise minio_error(f"Could not access file size for {name}", error)

    def _presigned_url(
        self, name: str, max_age: T.Optional[datetime.timedelta] = None
    ) -> str:
        kwargs = {}
        if max_age is not None:
            kwargs["expires"] = max_age

        client = self.client if self.base_url is None else self.base_url_client
        url = client.presigned_get_object(self.bucket_name, name, **kwargs)

        if self.base_url is not None:
            url_parts = urlsplit(url)
            base_url_parts = urlsplit(self.base_url)

            # It's assumed that self.base_url will contain bucket information,
            # which could be different, so remove the bucket_name component (with 1
            # extra character for the leading "/") from the generated URL
            url_key_path = url_parts.path[len(self.bucket_name) + 1 :]

            # Prefix the URL with any path content from base_url
            new_url_path = base_url_parts.path + url_key_path

            # Reconstruct the URL with an updated path
            url = urlunsplit(
                (
                    url_parts.scheme,
                    url_parts.netloc,
                    new_url_path,
                    url_parts.query,
                    url_parts.fragment,
                )
            )
        return url

    def url(
        self, name: str, *args, max_age: T.Optional[datetime.timedelta] = None
    ) -> str:
        if self.presign_urls:
            url = self._presigned_url(name, max_age=max_age)
        else:
            if self.base_url is not None:

                def strip_beg(path):
                    while path.startswith("/"):
                        path = path[1:]
                    return path

                def strip_end(path):
                    while path.endswith("/"):
                        path = path[:-1]
                    return path

                url = "{}/{}".format(
                    strip_end(self.base_url), urllib.parse.quote(strip_beg(name))
                )
            else:
                url = get_target_url(
                    self.client._endpoint_url,
                    bucket_name=self.bucket_name,
                    object_name=name,
                    # bucket_region=region,
                )
        return url

    def accessed_time(self, name: str) -> datetime.datetime:
        """
        Not available via the S3 API
        """
        return self.modified_time(name)

    def created_time(self, name: str) -> datetime.datetime:
        """
        Not available via the S3 API
        """
        return self.modified_time(name)

    def modified_time(self, name: str) -> datetime.datetime:
        try:
            info = self.client.stat_object(self.bucket_name, name)
            return datetime.datetime.fromtimestamp(mktime(info.last_modified))
        except merr.ResponseError as error:
            raise minio_error(
                f"Could not access modification time for file {name}", error
            )


_NoValue = object()


def get_setting(name, default=_NoValue):
    result = getattr(settings, name, default)
    if result is _NoValue:
        # print("Attr {} : {}".format(name, getattr(settings, name, default)))
        raise ImproperlyConfigured
    else:
        return result


def create_minio_client_from_settings(*, minio_kwargs=dict()):
    endpoint = get_setting("MINIO_STORAGE_ENDPOINT")
    access_key = get_setting("MINIO_STORAGE_ACCESS_KEY")
    secret_key = get_setting("MINIO_STORAGE_SECRET_KEY")
    secure = get_setting("MINIO_STORAGE_USE_HTTPS", True)
    # Making this client deconstructible allows it to be passed directly as
    # an argument to MinioStorage, since Django needs to be able to
    # deconstruct all Storage constructor arguments for Storages referenced in
    # migrations (e.g. when using a custom storage on a FileField).
    client = deconstructible(minio.Minio)(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
        **minio_kwargs,
    )
    return client


@deconstructible
class MinioMediaStorage(MinioStorage):
    def __init__(self):
        client = create_minio_client_from_settings()
        bucket_name = get_setting("MINIO_STORAGE_MEDIA_BUCKET_NAME")
        base_url = get_setting("MINIO_STORAGE_MEDIA_URL", None)
        auto_create_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET", False
        )
        auto_create_policy = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY", "GET_ONLY"
        )

        policy_type = Policy.get
        if isinstance(auto_create_policy, str):
            policy_type = Policy(auto_create_policy)
            auto_create_policy = True

        presign_urls = get_setting("MINIO_STORAGE_MEDIA_USE_PRESIGNED", False)
        backup_format = get_setting("MINIO_STORAGE_MEDIA_BACKUP_FORMAT", False)
        backup_bucket = get_setting("MINIO_STORAGE_MEDIA_BACKUP_BUCKET", False)

        assume_bucket_exists = get_setting(
            "MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS", False
        )

        object_metadata = get_setting("MINIO_STORAGE_MEDIA_OBJECT_METADATA", None)
        # print("SETTING", object_metadata)

        super().__init__(
            client,
            bucket_name,
            auto_create_bucket=auto_create_bucket,
            auto_create_policy=auto_create_policy,
            policy_type=policy_type,
            base_url=base_url,
            presign_urls=presign_urls,
            backup_format=backup_format,
            backup_bucket=backup_bucket,
            assume_bucket_exists=assume_bucket_exists,
            object_metadata=object_metadata,
        )


@deconstructible
class MinioStaticStorage(MinioStorage):
    def __init__(self):
        client = create_minio_client_from_settings()
        base_url = get_setting("MINIO_STORAGE_STATIC_URL", None)
        bucket_name = get_setting("MINIO_STORAGE_STATIC_BUCKET_NAME")
        auto_create_bucket = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET", False
        )
        auto_create_policy = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_STATIC_POLICY", "GET_ONLY"
        )

        policy_type = Policy.get
        if isinstance(auto_create_policy, str):
            policy_type = Policy(auto_create_policy)
            auto_create_policy = True

        presign_urls = get_setting("MINIO_STORAGE_STATIC_USE_PRESIGNED", False)

        assume_bucket_exists = get_setting(
            "MINIO_STORAGE_ASSUME_STATIC_BUCKET_EXISTS", False
        )

        object_metadata = get_setting("MINIO_STORAGE_STATIC_OBJECT_METADATA", None)

        super().__init__(
            client,
            bucket_name,
            auto_create_bucket=auto_create_bucket,
            auto_create_policy=auto_create_policy,
            policy_type=policy_type,
            base_url=base_url,
            presign_urls=presign_urls,
            assume_bucket_exists=assume_bucket_exists,
            object_metadata=object_metadata,
        )
