import enum
import json
import typing


class Policy(enum.Enum):
    read_only = "READ_ONLY"
    write_only = "WRITE_ONLY"
    read_write = "READ_WRITE"

    def bucket(
        self, bucket_name: str, *, json_encode: bool = True
    ) -> typing.Union[str, typing.Dict[str, typing.Any]]:
        policies = {
            Policy.read_only: _read_only,
            Policy.write_only: _write_only,
            Policy.read_write: _read_write,
        }
        pol = policies[self](bucket_name)
        if json_encode:
            return json.dumps(pol)
        return pol


def _read_only(bucket_name: str) -> typing.Dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:GetBucketLocation",
                "Resource": f"arn:aws:s3:::{bucket_name}",
            },
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:ListBucket",
                "Resource": f"arn:aws:s3:::{bucket_name}",
            },
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
            },
        ],
    }


def _write_only(bucket_name: str) -> typing.Dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:GetBucketLocation",
                "Resource": f"arn:aws:s3:::{bucket_name}",
            },
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "s3:ListBucketMultipartUploads",
                "Resource": f"arn:aws:s3:::{bucket_name}",
            },
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": [
                    "s3:ListMultipartUploadParts",
                    "s3:AbortMultipartUpload",
                    "s3:DeleteObject",
                    "s3:PutObject",
                ],
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
            },
        ],
    }


def _read_write(bucket_name: str) -> typing.Dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["s3:GetBucketLocation"],
                "Sid": "",
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
            },
            {
                "Action": ["s3:ListBucket"],
                "Sid": "",
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
            },
            {
                "Action": ["s3:ListBucketMultipartUploads"],
                "Sid": "",
                "Resource": [f"arn:aws:s3:::{bucket_name}"],
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
            },
            {
                "Action": [
                    "s3:ListMultipartUploadParts",
                    "s3:GetObject",
                    "s3:AbortMultipartUpload",
                    "s3:DeleteObject",
                    "s3:PutObject",
                ],
                "Sid": "",
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
            },
        ],
    }
