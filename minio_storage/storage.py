import dataclasses
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
            credentials=client._provider,
            secure=base_url_parts.scheme == "https",
            # The bucket region may be auto-detected by client (via an HTTP
            # request), so don't just use client._region
            region=client._get_region(bucket_name, None),
            http_client=client._http,
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

    def _open(self, name, mode="rb"):
        try:
            f = self.file_class(self._sanitize_path(name), mode, self)
        except merr.MinioException as e:
            raise minio_error(f"File {name} could not be saved: {str(e)}", e)
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
                metadata=self.object_metadata,
            )
            return sane_name
        except merr.InvalidResponseError as error:
            raise minio_error(f"File {name} could not be saved", error)

    def delete(self, name: str) -> None:
        if self.backup_format and self.backup_bucket:
            try:
                obj = self.client.get_object(self.bucket_name, name)
            except merr.InvalidResponseError as error:
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
            except merr.InvalidResponseError as error:
                raise minio_error(
                    "Could not make a copy of file "
                    "{} before removing it".format(name),
                    error,
                )

        try:
            self.client.remove_object(self.bucket_name, name)
        except merr.InvalidResponseError as error:
            raise minio_error(f"Could not remove file {name}", error)

    def exists(self, name: str) -> bool:
        try:
            self.client.stat_object(self.bucket_name, self._sanitize_path(name))
            return True
        except merr.InvalidResponseError as error:
            # TODO - deprecate
            if error._code == "NoSuchKey":
                return False
            else:
                raise minio_error(f"Could not stat file {name}", error)
        except merr.S3Error:
            return False
        except Exception as error:
            logger.error(error)
        return False

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
            objects = self.client.list_objects(self.bucket_name, prefix=path)
            for o in objects:
                p = posixpath.relpath(o.object_name, path)
                if o.is_dir:
                    dirs.append(p)
                else:
                    files.append(p)
            return dirs, files
        except merr.S3Error:
            raise
        except merr.InvalidResponseError as error:
            raise minio_error(f"Could not list directory {path}", error)

    def size(self, name: str) -> int:
        try:
            info: Object = self.client.stat_object(self.bucket_name, name)
            return info.size  # type: ignore
        except merr.InvalidResponseError as error:
            raise minio_error(f"Could not access file size for {name}", error)

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
        if url:
            return str(url)
        return None

    def url(
        self, name: str, *args, max_age: T.Optional[datetime.timedelta] = None
    ) -> str:
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
                url = "{}/{}".format(strip_end(self.base_url), quote(strip_beg(name)))
            else:
                url = "{}/{}/{}".format(
                    strip_end(self.endpoint_url),
                    self.bucket_name,
                    quote(strip_beg(name)),
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
            if info.last_modified:
                return info.last_modified  # type: ignore
        except merr.InvalidResponseError as error:
            raise minio_error(
                f"Could not access modification time for file {name}", error
            )
        raise OSError(f"Could not access modification time for file {name}")


_NoValue = object()


def get_setting(name: str, default=_NoValue) -> T.Any:
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


NoValue = object()

SettingsGenerator = T.Callable[[], "Settings"]


@dataclasses.dataclass
class Settings:
    bucket: T.Union[T.Literal[NoValue], None, str] = NoValue
    # file_class: T.Union[T.Literal[NoValue], None, str] = NoValue

    base_url: T.Union[T.Literal[NoValue], None, str] = NoValue
    auto_create_bucket: T.Union[T.Literal[NoValue], None, str] = NoValue
    auto_create_policy: T.Union[T.Literal[NoValue], None, str] = NoValue

    # minio client settings
    endpoint: T.Union[T.Literal[NoValue], str] = NoValue
    access_key: T.Union[T.Literal[NoValue], str] = NoValue
    secret_key: T.Union[T.Literal[NoValue], str] = NoValue
    secure: T.Union[T.Literal[NoValue], bool] = NoValue

    policy_type: T.Union[T.Literal[NoValue], None, str] = NoValue
    presign_urls: T.Union[T.Literal[NoValue], bool] = NoValue
    assume_bucket_exists: T.Union[T.Literal[NoValue], None, bool] = NoValue
    backup_format: T.Union[T.Literal[NoValue], None, str] = NoValue
    backup_bucket: T.Union[T.Literal[NoValue], None, str] = NoValue
    object_metadata: T.Union[T.Literal[NoValue], None, T.Dict] = NoValue

    def dict(self) -> T.Dict:
        result = {}
        for field in dataclasses.fields(self):
            v = getattr(self, field.name)
            if v is not NoValue:
                result[field.name] = v
        return result

    def storage_kwargs(self) -> T.Dict:
        result = {}
        for field in dataclasses.fields(self):
            if field.name in [
                "endpoint",
                "access_key",
                "secret_key",
                "secure",
                "bucket",
            ]:
                continue
            v = getattr(self, field.name)
            if v is not NoValue:
                result[field.name] = v

        return result

    def minio_client(self, **kwargs) -> minio.Minio:
        kw = {}
        kw.update(kwargs)
        for field in ["access_key", "secret_key", "secure"]:
            v = getattr(self, field, NoValue)
            if v is not NoValue:
                kw[field] = v
        client = minio.Minio(self.endpoint, **kw)
        return client

    # @property
    def validate(self):
        pass

    @classmethod
    def from_django_settings(cls, name: str) -> "Settings":
        """create Settings object instance from django settings."""
        result = cls()
        setting = getattr(settings, name, NoValue)
        if setting is NoValue:
            return cls
        field_names = [v.name for v in dataclasses.fields(result)]
        for field in field_names:
            v = getattr(setting, field, NoValue)
            if result is not NoValue:
                setattr(result, field, v)

    @classmethod
    def merge(cls, *settings: "Settings"):
        """merge multiple Settings object instances."""
        result = cls()
        field_names = [v.name for v in dataclasses.fields(result)]
        for s in settings:
            for field in field_names:
                v = getattr(s, field)
                if v is not NoValue:
                    setattr(result, field, v)
        return result

    @classmethod
    def create(cls, *generators: SettingsGenerator):
        return cls.merge(*[sg() for sg in generators])


def default_settings() -> T.Callable[[], Settings]:
    def f() -> Settings:
        return Settings(
            auto_create_bucket=False,
            auto_create_policy="GET_ONLY",
            presign_urls=False,
            assume_bucket_exists=False,
            secure=False,
        )

    return f


def django_settings(name: str) -> T.Callable[[], Settings]:
    def f() -> Settings:
        return Settings.from_django_settings(name)

    return f


def django_settings_compat(name: str) -> T.Callable[[], Settings]:
    """The old style configuration"""

    def f() -> Settings:
        s = Settings()

        def get_setting(field, name):
            v = getattr(settings, name, NoValue)
            if v is not NoValue:
                setattr(s, field, v)

        get_setting("endpoint", "MINIO_STORAGE_ENDPOINT")
        get_setting("access_key", "MINIO_STORAGE_ACCESS_KEY")
        get_setting("secret_key", "MINIO_STORAGE_SECRET_KEY")
        get_setting("use_https", "MINIO_STORAGE_USE_HTTPS")

        get_setting("bucket", f"MINIO_STORAGE_{name}_BUCKET_NAME")
        get_setting("base_url", f"MINIO_STORAGE_{name}_URL")
        get_setting("auto_create_bucket", f"MINIO_STORAGE_AUTO_CREATE_{name}_BUCKET")
        get_setting("auto_create_policy", f"MINIO_STORAGE_AUTO_CREATE_{name}_POLICY")
        get_setting("presign_urls", f"MINIO_STORAGE_{name}_USE_PRESIGNED")
        get_setting("backup_format", f"MINIO_STORAGE_{name}_BACKUP_FORMAT")
        get_setting("backup_bucket", f"MINIO_STORAGE_{name}_BACKUP_BUCKET")
        get_setting(
            "assume_bucket_exists", f"MINIO_STORAGE_{name}_ASSUME_BUCKET_EXISTS"
        )
        get_setting("object_metadata", f"MINIO_STORAGE_{name}_OBJECT_METADATA")

        return s

    return f


@deconstructible
class MinioMediaStorage(MinioStorage):
    def __init__(self):
        settings = Settings.create(
            default_settings(),
            django_settings_compat("MEDIA"),
            django_settings("MINIO"),
            django_settings("MINIO_MEDIA"),
        )
        client = settings.minio_client()
        kwargs = settings.storage_kwargs()

        super().__init__(
            client,
            settings.bucket,
            **kwargs,
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
