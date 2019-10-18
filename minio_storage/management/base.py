from unittest.mock import patch

import minio_storage.storage
from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string


class StorageCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--class",
            type=str,
            default="minio_storage.storage.MinioMediaStorage",
            help="Storage class to modify "
            "(media/static are short names for default classes)",
        )

        parser.add_argument(
            "--bucket",
            type=str,
            default=None,
            help="bucket name (will use storage class bucket if not set)",
        )

    def storage(self, options):
        class_name = {
            "media": "minio_storage.storage.MinioMediaStorage",
            "static": "minio_storage.storage.MinioStaticStorage",
        }.get(options["class"], options["class"])

        try:
            storage_class = import_string(class_name)
        except ImportError:
            raise CommandError(f"could not find storage class: {class_name}")
        if not issubclass(storage_class, minio_storage.storage.MinioStorage):
            raise CommandError(f"{class_name} is not an sub class of MinioStorage.")

        # TODO: maybe another way
        with patch.object(storage_class, "_init_check", return_value=None):
            storage = storage_class()
            return storage
