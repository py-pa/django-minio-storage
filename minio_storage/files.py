import tempfile
import typing as T
from logging import getLogger

from django.core.files.base import File
from minio import error as merr

from minio_storage.errors import minio_error

if T.TYPE_CHECKING:
    from minio_storage.storage import Storage

logger = getLogger("minio_storage")


class ReadOnlyMixin:
    """File class mixin which disallows .write() calls"""

    def writable(self) -> bool:
        return False

    def write(*args, **kwargs):
        raise NotImplementedError("this is a read only file")


class NonSeekableMixin:
    """File class mixin which disallows .seek() calls"""

    def seekable(self) -> bool:
        return False

    def seek(self, *args, **kwargs) -> bool:
        # TODO: maybe exception is better
        # raise NotImplementedError('seek is not supported')
        return False


class MinioStorageFile(File):
    def __init__(self, name: str, mode: str, storage: "Storage", **kwargs):
        self._storage: "Storage" = storage
        self.name: str = name
        self._mode: str = mode
        self._file = None


class ReadOnlyMinioObjectFile(MinioStorageFile, ReadOnlyMixin, NonSeekableMixin):
    """A django File class which directly exposes the underlying minio object. This
    means the the instance doesnt support functions like .seek() and is required to
    be closed to be able to reuse minio connections.

    Note: This file class is not tested yet"""

    def __init__(
        self,
        name: str,
        mode: str,
        storage: "Storage",
        max_memory_size: T.Optional[int] = None,
        **kwargs,
    ):
        if mode.find("w") > -1:
            raise NotImplementedError(
                "ReadOnlyMinioObjectFile storage only support read modes"
            )
        if max_memory_size is not None:
            self.max_memory_size = max_memory_size
        super().__init__(name, mode, storage)

    def _get_file(self):
        if self._file is None:
            try:
                obj = self._storage.client.get_object(
                    self._storage.bucket_name, self.name
                )
                self._file = obj
                return self._file
            except merr.ResponseError as error:
                logger.warn(error)
                raise OSError(f"File {self.name} does not exist")
            finally:
                try:
                    obj.release_conn()
                except Exception as e:
                    logger.error(str(e))
        return self._file

    def _set_file(self, value):
        self._file = value

    file = property(_get_file, _set_file)

    def close(self):
        try:
            self.file.close()
        finally:
            self.file.release_conn()


class ReadOnlySpooledTemporaryFile(MinioStorageFile, ReadOnlyMixin):
    """A django File class which buffers the minio object into a local
    SpooledTemporaryFile."""

    max_memory_size: int = 1024 * 1024 * 10

    def __init__(
        self,
        name: str,
        mode: str,
        storage: "Storage",
        max_memory_size: T.Optional[int] = None,
        **kwargs,
    ):
        if mode.find("w") > -1:
            raise NotImplementedError(
                "ReadOnlySpooledTemporaryFile storage only support read modes"
            )
        if max_memory_size is not None:
            self.max_memory_size = max_memory_size
        super().__init__(name, mode, storage)

    def _get_file(self):
        if self._file is None:
            try:
                obj = self._storage.client.get_object(
                    self._storage.bucket_name, self.name
                )
                self._file = tempfile.SpooledTemporaryFile(
                    max_size=self.max_memory_size
                )
                for d in obj.stream(amt=1024 * 1024):
                    self._file.write(d)
                self._file.seek(0)
                return self._file
            except merr.ResponseError as error:
                raise minio_error(f"File {self.name} does not exist", error)
            finally:
                try:
                    obj.release_conn()
                except Exception as e:
                    logger.error(str(e))
        return self._file

    def _set_file(self, value):
        self._file = value

    file = property(_get_file, _set_file)

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
