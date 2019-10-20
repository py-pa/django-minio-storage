import sys

import minio.error
from django.core.management.base import CommandError, no_translations
from minio_storage.management.base import StorageCommand


class Command(StorageCommand):
    help = "verify, list, create and delete minio buckets"

    def add_arguments(self, parser):
        group = parser.add_argument_group("bucket actions")
        group.add_argument("--create", action="store_true", help="create bucket")
        group.add_argument("--delete", action="store_true", help="delete bucket")
        group = parser.add_argument_group("bucket show options")
        group.add_argument("--files", action="store_true", help="show files")
        group.add_argument("--prefix", type=str, default="", help="path prefix")
        super().add_arguments(parser)

    @no_translations
    def handle(self, *args, **options):
        storage = self.storage(options)
        bucket_name = options["bucket"] or storage.bucket_name

        if options["create"] and options["delete"]:
            raise CommandError("--create and --delete are mutually exclusive")

        if options["create"]:
            try:
                storage.client.make_bucket(bucket_name)
                print(f"created bucket: {bucket_name}", file=sys.stderr)
            except minio.error.BucketAlreadyOwnedByYou:
                raise CommandError(f"you have already created {bucket_name}")
        elif options["delete"]:
            try:
                storage.client.remove_bucket(bucket_name)
            except minio.error.NoSuchBucket:
                raise CommandError(f"bucket {bucket_name} does not exist")
            except minio.error.BucketNotEmpty:
                raise CommandError(f"bucket {bucket_name} is not empty")
        else:
            exists = storage.client.bucket_exists(bucket_name)
            if not exists:
                raise CommandError(f"bucket {bucket_name} does not exist")

            objs = storage.client.list_objects_v2(bucket_name, prefix=options["prefix"])
            n_files = 0
            n_dirs = 0
            for o in objs:
                if o.is_dir:
                    n_dirs += 1
                    print(f"{o.object_name}")
                else:
                    n_files += 1
                    if options["files"]:
                        print(f"{o.object_name}")
            print(f"{n_files} files and {n_dirs} directories", file=sys.stderr)
