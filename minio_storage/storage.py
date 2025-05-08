import datetime
import mimetypes
import posixpath
import typing as T
from logging import getLogger
from urllib.parse import quote, urlsplit, urlunsplit

import minio
import minio.error as merr
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import Storage
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from minio.datatypes import Object

from minio_storage.errors import minio_error
from minio_storage.files import MinioStorageFile, ReadOnlySpooledTemporaryFile
from minio_storage.policy import Policy

logger = getLogger("minio_storage")

ObjectMetadataType = T.Mapping[str, T.Union[str, list[str], tuple[str]]]


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
        file_class: T.Optional[type[MinioStorageFile]] = None,
        auto_create_bucket: bool = False,
        presign_urls: bool = False,
        auto_create_policy: bool = False,
        policy_type: T.Optional[Policy] = None,
        object_metadata: T.Optional[ObjectMetadataType] = None,
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
            credentials=client._provider,
            secure=base_url_parts.scheme == "https",
            # The bucket region may be auto-detected by client (via an HTTP
            # request), so don't just use client._region
            region=client._get_region(bucket_name),
            http_client=client._http,
            cert_check=get_setting("MINIO_STORAGE_CERT_CHECK",True)
        )

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

    def _open(self, name: str, mode: str = "rb") -> MinioStorageFile:
        try:
            f = self.file_class(self._sanitize_path(name), mode, self)
        except merr.MinioException as e:
            raise minio_error(f"File {name} could not be saved: {e!s}", e) from e
        return f

    def _save(self, name: str, content: T.BinaryIO) -> str:
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
                # Minio is annotated to expect a Dict, rather than a Mapping; we
                # annotate this type as Mapping, since only Mapping is covariant, which
                # is more friendly to users.
                metadata=self.object_metadata,  # type: ignore[arg-type]
            )
            return sane_name
        except merr.InvalidResponseError as error:
            raise minio_error(f"File {name} could not be saved", error) from error

    def delete(self, name: str) -> None:
        if self.backup_format and self.backup_bucket:
            try:
                obj = self.client.get_object(self.bucket_name, name)
            except merr.InvalidResponseError as error:
                raise minio_error(
                    f"Could not obtain file {name} to make a copy of it",
                    error,
                ) from error

            try:
                content_length = int(obj.headers.get("Content-Length", ""))
            except ValueError as error:
                raise minio_error(
                    f"Could not backup removed file {name}", error
                ) from error

            # Creates the backup filename
            target_name = f"{timezone.now().strftime(self.backup_format)}{name}"
            try:
                self.client.put_object(
                    self.backup_bucket,
                    target_name,
                    # This is expected to be a BinaryIO, but the actual
                    # BaseHTTPResponse "obj" still provides ".read() -> bytes".
                    obj,  # type: ignore[arg-type]
                    content_length,
                )
            except merr.InvalidResponseError as error:
                raise minio_error(
                    f"Could not make a copy of file {name} before removing it",
                    error,
                ) from error

        try:
            self.client.remove_object(self.bucket_name, name)
        except merr.InvalidResponseError as error:
            raise minio_error(f"Could not remove file {name}", error) from error

    def exists(self, name: str) -> bool:
        try:
            self.client.stat_object(self.bucket_name, self._sanitize_path(name))
            return True
        except merr.InvalidResponseError as error:
            # TODO - deprecate
            if error._code == "NoSuchKey":
                return False
            else:
                raise minio_error(f"Could not stat file {name}", error) from error
        except merr.S3Error:
            return False
        except Exception as error:
            logger.error(error)
        return False

    def listdir(self, path: str) -> tuple[list, list]:
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

        dirs: list[str] = []
        files: list[str] = []
        try:
            objects = self.client.list_objects(self.bucket_name, prefix=path)
            for o in objects:
                assert o.object_name is not None
                p = posixpath.relpath(o.object_name, path)
                if o.is_dir:
                    dirs.append(p)
                else:
                    files.append(p)
            return dirs, files
        except merr.S3Error:
            raise
        except merr.InvalidResponseError as error:
            raise minio_error(f"Could not list directory {path}", error) from error

    def size(self, name: str) -> int:
        try:
            info: Object = self.client.stat_object(self.bucket_name, name)
        except merr.InvalidResponseError as error:
            raise minio_error(
                f"Could not access file size for {name}", error
            ) from error
        assert info.size is not None
        return info.size

    def _presigned_url(
        self, name: str, max_age: T.Optional[datetime.timedelta] = None
    ) -> T.Optional[str]:
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
            url_key_path = url_parts.path[len(self.bucket_name) + 1 :]  # noqa: E203

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
        if url:
            return str(url)
        return None

    # Django allows "name" to be None, but types should indicate that this is disallowed
    @T.overload
    def url(
        self, name: None, *, max_age: T.Optional[datetime.timedelta] = ...
    ) -> T.NoReturn: ...

    @T.overload
    def url(
        self, name: str, *, max_age: T.Optional[datetime.timedelta] = ...
    ) -> str: ...

    def url(
        self, name: T.Optional[str], *, max_age: T.Optional[datetime.timedelta] = None
    ) -> str:
        if name is None:
            raise ValueError("name may not be None")
        url = ""
        if self.presign_urls:
            url = self._presigned_url(name, max_age=max_age)
        else:

            def strip_beg(path):
                while path.startswith("/"):
                    path = path[1:]
                return path

            def strip_end(path):
                while path.endswith("/"):
                    path = path[:-1]
                return path

            if self.base_url is not None:
                url = f"{strip_end(self.base_url)}/{quote(strip_beg(name))}"
            else:
                url = (
                    f"{strip_end(self.endpoint_url)}/{self.bucket_name}/"
                    f"{quote(strip_beg(name))}"
                )
        if url:
            return url
        raise OSError(f"could not produce URL for {name}")

    @property
    def endpoint_url(self):
        return self.client._base_url._url.geturl()

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
            info: Object = self.client.stat_object(self.bucket_name, name)
        except merr.InvalidResponseError as error:
            raise minio_error(
                f"Could not access modification time for file {name}", error
            ) from error
        if info.last_modified is None:
            raise OSError(f"Could not access modification time for file {name}")
        return info.last_modified


_NoValue = object()


def get_setting(name: str, default=_NoValue) -> T.Any:
    result = getattr(settings, name, default)
    if result is _NoValue:
        # print("Attr {} : {}".format(name, getattr(settings, name, default)))
        raise ImproperlyConfigured
    else:
        return result


def create_minio_client_from_settings(*, minio_kwargs=None):
    endpoint = get_setting("MINIO_STORAGE_ENDPOINT")
    kwargs = {
        "access_key": get_setting("MINIO_STORAGE_ACCESS_KEY"),
        "secret_key": get_setting("MINIO_STORAGE_SECRET_KEY"),
        "secure": get_setting("MINIO_STORAGE_USE_HTTPS", True),
        "cert_check": get_setting("MINIO_STORAGE_CERT_CHECK",True),
    }
    region = get_setting("MINIO_STORAGE_REGION", None)
    if region:
        kwargs["region"] = region

    if minio_kwargs:
        kwargs.update(minio_kwargs)

    # Making this client deconstructible allows it to be passed directly as
    # an argument to MinioStorage, since Django needs to be able to
    # deconstruct all Storage constructor arguments for Storages referenced in
    # migrations (e.g. when using a custom storage on a FileField).
    client = deconstructible(minio.Minio)(
        endpoint,
        **kwargs,
    )
    return client


@deconstructible
class MinioMediaStorage(MinioStorage):
    def __init__(  # noqa: C901
        self,
        *,
        minio_client: T.Optional[minio.Minio] = None,
        bucket_name: T.Optional[str] = None,
        base_url: T.Optional[str] = None,
        file_class: T.Optional[type[MinioStorageFile]] = None,
        auto_create_bucket: T.Optional[bool] = None,
        presign_urls: T.Optional[bool] = None,
        auto_create_policy: T.Optional[bool] = None,
        policy_type: T.Optional[Policy] = None,
        object_metadata: T.Optional[ObjectMetadataType] = None,
        backup_format: T.Optional[str] = None,
        backup_bucket: T.Optional[str] = None,
        assume_bucket_exists: T.Optional[bool] = None,
    ):
        if minio_client is None:
            minio_client = create_minio_client_from_settings()
        if bucket_name is None:
            bucket_name = get_setting("MINIO_STORAGE_MEDIA_BUCKET_NAME")
            assert bucket_name is not None
        if base_url is None:
            base_url = get_setting("MINIO_STORAGE_MEDIA_URL", None)
        if auto_create_bucket is None:
            auto_create_bucket = get_setting(
                "MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET", False
            )
            assert auto_create_bucket is not None
        if presign_urls is None:
            presign_urls = get_setting("MINIO_STORAGE_MEDIA_USE_PRESIGNED", False)
            assert presign_urls is not None
        auto_create_policy_setting = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY", "GET_ONLY"
        )
        if auto_create_policy is None:
            auto_create_policy = (
                True
                if isinstance(auto_create_policy_setting, str)
                else auto_create_policy_setting
            )
            assert auto_create_policy is not None
        if policy_type is None:
            policy_type = (
                Policy(auto_create_policy_setting)
                if isinstance(auto_create_policy_setting, str)
                else Policy.get
            )
            assert policy_type is not None
        if object_metadata is None:
            object_metadata = get_setting("MINIO_STORAGE_MEDIA_OBJECT_METADATA", None)
        if backup_format is None:
            backup_format = get_setting("MINIO_STORAGE_MEDIA_BACKUP_FORMAT", None)
        if backup_bucket is None:
            backup_bucket = get_setting("MINIO_STORAGE_MEDIA_BACKUP_BUCKET", None)
        if assume_bucket_exists is None:
            assume_bucket_exists = get_setting(
                "MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS", False
            )
            assert assume_bucket_exists is not None

        super().__init__(
            minio_client,
            bucket_name,
            base_url=base_url,
            file_class=file_class,
            auto_create_bucket=auto_create_bucket,
            presign_urls=presign_urls,
            auto_create_policy=auto_create_policy,
            policy_type=policy_type,
            object_metadata=object_metadata,
            backup_format=backup_format,
            backup_bucket=backup_bucket,
            assume_bucket_exists=assume_bucket_exists,
        )


@deconstructible
class MinioStaticStorage(MinioStorage):
    def __init__(
        self,
        *,
        minio_client: T.Optional[minio.Minio] = None,
        bucket_name: T.Optional[str] = None,
        base_url: T.Optional[str] = None,
        file_class: T.Optional[type[MinioStorageFile]] = None,
        auto_create_bucket: T.Optional[bool] = None,
        presign_urls: T.Optional[bool] = None,
        auto_create_policy: T.Optional[bool] = None,
        policy_type: T.Optional[Policy] = None,
        object_metadata: T.Optional[ObjectMetadataType] = None,
        assume_bucket_exists: T.Optional[bool] = None,
    ):
        if minio_client is None:
            minio_client = create_minio_client_from_settings()
        if bucket_name is None:
            bucket_name = get_setting("MINIO_STORAGE_STATIC_BUCKET_NAME")
            assert bucket_name is not None
        if base_url is None:
            base_url = get_setting("MINIO_STORAGE_STATIC_URL", None)
        if auto_create_bucket is None:
            auto_create_bucket = get_setting(
                "MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET", False
            )
            assert auto_create_bucket is not None
        if presign_urls is None:
            presign_urls = get_setting("MINIO_STORAGE_STATIC_USE_PRESIGNED", False)
            assert presign_urls is not None
        auto_create_policy_setting = get_setting(
            "MINIO_STORAGE_AUTO_CREATE_STATIC_POLICY", "GET_ONLY"
        )
        if auto_create_policy is None:
            auto_create_policy = (
                True
                if isinstance(auto_create_policy_setting, str)
                else auto_create_policy_setting
            )
            assert auto_create_policy is not None
        if policy_type is None:
            policy_type = (
                Policy(auto_create_policy_setting)
                if isinstance(auto_create_policy_setting, str)
                else Policy.get
            )
            assert policy_type is not None
        if object_metadata is None:
            object_metadata = get_setting("MINIO_STORAGE_STATIC_OBJECT_METADATA", None)
        if assume_bucket_exists is None:
            assume_bucket_exists = get_setting(
                "MINIO_STORAGE_ASSUME_STATIC_BUCKET_EXISTS", False
            )
            assert assume_bucket_exists is not None

        super().__init__(
            minio_client,
            bucket_name,
            base_url=base_url,
            file_class=file_class,
            auto_create_bucket=auto_create_bucket,
            presign_urls=presign_urls,
            auto_create_policy=auto_create_policy,
            policy_type=policy_type,
            object_metadata=object_metadata,
            # backup_format and backup_bucket are not valid for static storage
            assume_bucket_exists=assume_bucket_exists,
        )
