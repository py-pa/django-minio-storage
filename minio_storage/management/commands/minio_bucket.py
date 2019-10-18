import sys

import minio.error
from django.core.management.base import CommandError, no_translations
from minio_storage.management.base import StorageCommand


class Command(StorageCommand):
    help = "create storage class bucket"

    def add_arguments(self, parser):
        super().add_arguments(parser)

    @no_translations
    def handle(self, *args, **options):
        storage = self.storage(options)
        bucket_name = options["bucket"] or storage.bucket_name
        try:
            storage.client.make_bucket(bucket_name)
            print(f"created bucket: {bucket_name}", file=sys.stderr)
        except minio.error.BucketAlreadyOwnedByYou:
            raise CommandError(f"you have already created {bucket_name}")
