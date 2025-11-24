import json
import sys
import typing as T
from string import Template
from unittest.mock import patch

import minio.error
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils.module_loading import import_string
from minio.datatypes import Object

from minio_storage.policy import Policy
from minio_storage.storage import MinioStorage


class Command(BaseCommand):
    help = "verify, list, create and delete minio buckets"

    CHECK = "check"
    CREATE = "create"
    DELETE = "delete"
    LIST = "ls"
    POLICY = "policy"

    FULL_FORMAT = "$name $size $modified $url $etag"

    def add_arguments(self, parser: CommandParser) -> None:
        group = parser.add_argument_group("minio")
        group.add_argument(
            "--class",
            type=str,
            default="minio_storage.MinioMediaStorage",
            help="Storage class to modify "
            "(media/static are short names for default classes)",
        )
        group.add_argument(
            "--bucket",
            type=str,
            default=None,
            help="bucket name (default: storage defined bucket if not set)",
        )

        cmds = parser.add_subparsers(
            dest="command",
            title="subcommands",
            description="valid subcommands",
            # required=True,
        )
        cmds.add_parser(self.CHECK, help="check bucket")
        cmds.add_parser(self.CREATE, help="make bucket")
        cmds.add_parser(self.DELETE, help="remove an empty bucket")

        ls = cmds.add_parser(self.LIST, help="list bucket objects or buckets")
        ls.add_argument("--dirs", action="store_true", help="include directories")
        ls.add_argument("--files", action="store_true", help="include files")
        ls.add_argument(
            "-r", "--recursive", action="store_true", help="find files recursive"
        )
        ls.add_argument("-p", "--prefix", type=str, default="", help="path prefix")
        ls.add_argument(
            "--buckets", action="store_true", help="list buckets instead of files"
        )
        ls.add_argument(
            "-f",
            "--format",
            type=str,
            default="$name",
            help="list format. ( $name $size $modified $url $etag )",
        )

        policy = cmds.add_parser(self.POLICY, help="get or set bucket policy")
        policy.add_argument(
            "--set",
            type=str,
            default=None,
            choices=[p.value for p in Policy],
            help="set bucket policy",
        )

        super().add_arguments(parser)

    def handle(self, *args, **options):
        storage = self.storage(options)
        bucket_name = options["bucket"] or storage.bucket_name
        command = options["command"] or ""
        if command == self.CHECK:
            return self.bucket_exists(storage, bucket_name)
        if command == self.CREATE:
            return self.bucket_create(storage, bucket_name)
        elif command == self.DELETE:
            return self.bucket_delete(storage, bucket_name)
        elif command == self.LIST:
            if options["buckets"]:
                return self.list_buckets(storage)

            list_dirs = True
            list_files = True
            summary = True
            if options["dirs"] or options["files"]:
                list_dirs = options["dirs"]
                list_files = options["files"]
                summary = False

            return self.bucket_list(
                storage,
                bucket_name,
                prefix=options["prefix"],
                list_dirs=list_dirs,
                list_files=list_files,
                recursive=options["recursive"],
                format=options["format"],
                summary=summary,
            )
        elif command == self.POLICY:
            if options["set"] is not None:
                return self.policy_set(
                    storage, bucket_name, policy=Policy(options["set"])
                )
            return self.policy_get(storage, bucket_name)
        self.print_help("minio", "")
        if command != "":
            raise CommandError(f"don't know how to handle command: {command}")
        raise CommandError("command name required")

    def storage(self, options) -> MinioStorage:
        class_name: str = options["class"]
        if class_name == "media":
            class_name = "minio_storage.MinioMediaStorage"
        elif class_name == "static":
            class_name = "minio_storage.MinioStaticStorage"

        try:
            storage_class = import_string(class_name)
        except ImportError as err:
            raise CommandError(f"could not find storage class: {class_name}") from err
        if not issubclass(storage_class, MinioStorage):
            raise CommandError(f"{class_name} is not an sub class of MinioStorage.")

        # TODO: maybe another way
        with patch.object(storage_class, "_init_check", return_value=None):
            # TODO: This constructor can be missing arguments
            storage = storage_class()  # pyright: ignore[reportCallIssue]
            return storage

    def bucket_exists(self, storage: MinioStorage, bucket_name: str) -> None:
        exists = storage.client.bucket_exists(bucket_name=bucket_name)
        if not exists:
            raise CommandError(f"bucket {bucket_name} does not exist")

    def list_buckets(self, storage: MinioStorage) -> None:
        objs = storage.client.list_buckets()
        for o in objs:
            self.stdout.write(f"{o.name}")

    def bucket_list(
        self,
        storage: MinioStorage,
        bucket_name: str,
        *,
        prefix: str,
        list_dirs: bool,
        list_files: bool,
        recursive: bool,
        format: T.Optional[str] = None,
        summary: bool = True,
    ) -> None:
        try:
            objs = storage.client.list_objects(
                bucket_name=bucket_name, prefix=prefix, recursive=recursive
            )

            template = None
            if format is not None and format != "$name":
                template = Template(format)

            def fmt(o: Object) -> str:
                if template is None:
                    return o.object_name or ""
                return template.substitute(
                    name=o.object_name,
                    size=o.size,
                    modified=o.last_modified,
                    etag=o.etag,
                    url=storage.url(o.object_name),
                )

            n_files = 0
            n_dirs = 0
            for o in objs:
                if o.is_dir:
                    n_dirs += 1
                    if list_dirs:
                        self.stdout.write(fmt(o))
                else:
                    n_files += 1
                    if list_files:
                        self.stdout.write(fmt(o))

            if summary:
                print(f"{n_files} files and {n_dirs} directories", file=sys.stderr)
        except minio.error.S3Error as e:
            raise CommandError(f"error reading bucket {bucket_name}") from e

    def bucket_create(self, storage: MinioStorage, bucket_name: str) -> None:
        try:
            storage.client.make_bucket(bucket_name=bucket_name)
            print(f"created bucket: {bucket_name}", file=sys.stderr)
        except minio.error.S3Error as e:
            raise CommandError(f"error creating {bucket_name}") from e
        return

    def bucket_delete(self, storage: MinioStorage, bucket_name: str) -> None:
        try:
            storage.client.remove_bucket(bucket_name=bucket_name)
        except minio.error.S3Error as err:
            if err.code == "BucketNotEmpty":
                raise CommandError(f"bucket {bucket_name} is not empty") from err
            elif err.code == "NoSuchBucket":
                raise CommandError(f"bucket {bucket_name} does not exist") from err

    def policy_get(self, storage: MinioStorage, bucket_name: str) -> str:
        try:
            policy = storage.client.get_bucket_policy(bucket_name=bucket_name)
            policy = json.loads(policy)
            policy = json.dumps(policy, ensure_ascii=False, indent=2)
            return policy
        except minio.error.S3Error as err:
            if err.code == "NoSuchBucket":
                raise CommandError(f"bucket {bucket_name} does not exist") from err
            elif err.code == "NoSuchBucketPolicy":
                raise CommandError(f"bucket {bucket_name} has no policy") from err
            raise

    def policy_set(
        self, storage: MinioStorage, bucket_name: str, policy: Policy
    ) -> None:
        try:
            policy = Policy(policy)
            storage.client.set_bucket_policy(
                bucket_name=bucket_name, policy=policy.bucket(bucket_name)
            )
        except minio.error.S3Error as e:
            raise CommandError(e.message) from e
