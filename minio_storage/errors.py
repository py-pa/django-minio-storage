import minio.error as merr


class MinIOError(OSError):
    def __init__(self, msg, cause):
        super().__init__(msg)
        self.cause = cause


reraise = {}
for v in (
    merr.APINotImplemented,
    merr.AccessDenied,
    merr.AccountProblem,
    merr.CredentialNotSupported,
    merr.CrossLocationLoggingProhibited,
    merr.ExpiredToken,
    merr.InvalidAccessKeyId,
    merr.InvalidAddressingHeader,
    merr.InvalidBucketError,
    merr.InvalidBucketName,
    merr.InvalidDigest,
    merr.InvalidEncryptionAlgorithmError,
    merr.InvalidEndpointError,
    merr.InvalidSecurity,
    merr.InvalidToken,
    merr.NoSuchBucket,
):
    reraise[v] = {"err": v}


def minio_error(msg, e):
    if e.__class__ in reraise:
        return e
    return MinIOError(msg, e)
