import minio.error as merr


class MinIOError(OSError):
    def __init__(self, msg, cause):
        super().__init__(msg)
        self.cause = cause


reraise = {}
for v in (
    merr.MinioException,
    merr.InvalidResponseError,
    merr.ServerError,
    merr.S3Error,
):
    reraise[v] = {"err": v}


def minio_error(msg, e):
    if e.__class__ in reraise:
        return e
    return MinIOError(msg, e)
