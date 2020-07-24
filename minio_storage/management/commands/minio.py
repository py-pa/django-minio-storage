import argparse
import json
import sys
from string import Template
from unittest.mock import patch

import minio.error
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string

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

    def add_arguments(self, parser):

        group = parser.add_argument_group("minio")
        group.add_argument(
            "--class",
            type=str,
            default="minio_storage.storage.MinioMediaStorage",
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
        cmds._parser_class = argparse.ArgumentParser  # circumvent Django 1.11 bug

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

    def storage(self, options):
        class_name = {
            "media": "minio_storage.storage.MinioMediaStorage",
            "static": "minio_storage.storage.MinioStaticStorage",
        }.get(options["class"], options["class"])

        try:
            storage_class = import_string(class_name)
        except ImportError:
            raise CommandError(f"could not find storage class: {class_name}")
        if not issubclass(storage_class, MinioStorage):
            raise CommandError(f"{class_name} is not an sub class of MinioStorage.")

        # TODO: maybe another way
        with patch.object(storage_class, "_init_check", return_value=None):
            storage = storage_class()
            return storage

    def bucket_exists(self, storage, bucket_name):
        exists = storage.client.bucket_exists(bucket_name)
        if not exists:
            raise CommandError(f"bucket {bucket_name} does not exist")

    def list_buckets(self, storage):
        objs = storage.client.list_buckets()
        for o in objs:
            self.stdout.write(f"{o.name}")

    def bucket_list(
        self,
        storage,
        bucket_name: str,
        *,
        prefix: str,
        list_dirs: bool,
        list_files: bool,
        recursive: bool,
        format: str = None,
        summary: bool = True,
    ):
        try:
            objs = storage.client.list_objects_v2(
                bucket_name, prefix=prefix, recursive=recursive
            )

            template = None
            if format is not None and format != "$name":
                template = Template(format)

            def fmt(o):
                if template is None:
                    return o.object_name
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
        except minio.error.NoSuchBucket:
            raise CommandError(f"bucket {bucket_name} does not exist")

    def bucket_create(self, storage, bucket_name):
        try:
            storage.client.make_bucket(bucket_name)
            print(f"created bucket: {bucket_name}", file=sys.stderr)
        except minio.error.BucketAlreadyOwnedByYou:
            raise CommandError(f"you have already created {bucket_name}")
        return

    def bucket_delete(self, storage, bucket_name):
        try:
            storage.client.remove_bucket(bucket_name)
        except minio.error.NoSuchBucket:
            raise CommandError(f"bucket {bucket_name} does not exist")
        except minio.error.BucketNotEmpty:
            raise CommandError(f"bucket {bucket_name} is not empty")

    def policy_get(self, storage, bucket_name):
        try:
            policy = storage.client.get_bucket_policy(bucket_name)
            policy = json.loads(policy)
            policy = json.dumps(policy, ensure_ascii=False, indent=2)
            return policy
        except minio.error.NoSuchBucket:
            raise CommandError(f"bucket {bucket_name} does not exist")
        except minio.error.NoSuchBucketPolicy:
            raise CommandError(f"bucket {bucket_name} has no policy")

    def policy_set(self, storage, bucket_name, policy: Policy):
        try:
            policy = Policy(policy)
            storage.client.set_bucket_policy(bucket_name, policy.bucket(bucket_name))
        except minio.error.NoSuchBucket as e:
            raise CommandError(e.message)
