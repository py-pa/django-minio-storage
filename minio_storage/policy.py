import enum
import json
import typing as T


class Policy(enum.Enum):
    none = "NONE"
    get = "GET_ONLY"
    read = "READ_ONLY"
    write = "WRITE_ONLY"
    read_write = "READ_WRITE"

    def bucket(
        self, bucket_name: str, *, json_encode: bool = True
    ) -> T.Union[str, T.Dict[str, T.Any]]:
        policies = {
            Policy.get: _get,
            Policy.read: _read,
            Policy.write: _write,
            Policy.read_write: _read_write,
            Policy.none: _none,
        }
        pol = policies[self](bucket_name)
        if json_encode:
            return json.dumps(pol)
        return pol


def _none(bucket_name: str) -> T.Dict:
    return {"Version": "2012-10-17", "Statement": []}


def _get(bucket_name: str) -> T.Dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
            }
        ],
    }


def _read(bucket_name: str) -> T.Dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetBucketLocation"],
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
            },
        ],
    }


def _write(bucket_name: str) -> T.Dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetBucketLocation"],
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:ListBucketMultipartUploads"],
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": [
                    "s3:ListMultipartUploadParts",
                    "s3:AbortMultipartUpload",
                    "s3:DeleteObject",
                    "s3:PutObject",
                ],
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
            },
        ],
    }


def _read_write(bucket_name: str) -> T.Dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetBucketLocation"],
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:ListBucketMultipartUploads"],
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": [
                    "s3:AbortMultipartUpload",
                    "s3:DeleteObject",
                    "s3:GetObject",
                    "s3:ListMultipartUploadParts",
                    "s3:PutObject",
                ],
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
            },
        ],
    }
