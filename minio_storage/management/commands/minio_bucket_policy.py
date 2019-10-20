import json

import minio.error
from django.core.management.base import CommandError, no_translations
from minio_storage.management.base import StorageCommand
from minio_storage.policy import Policy


class Command(StorageCommand):
    help = "View and set Minio bucket policies"

    def add_arguments(self, parser):
        super().add_arguments(parser)

        choices = [p.value for p in Policy]
        parser.add_argument("policy", nargs="?", type=str, choices=choices)

    @no_translations
    def handle(self, *args, **options):
        storage = self.storage(options)
        bucket_name = options["bucket"] or storage.bucket_name
        if options["policy"] is None:
            try:
                policy = storage.client.get_bucket_policy(bucket_name)
                policy = json.loads(policy)
                policy = json.dumps(policy, ensure_ascii=False, indent=2)
                print(policy)
            except (minio.error.NoSuchBucket, minio.error.NoSuchBucketPolicy) as e:
                raise CommandError(e.message)

        else:
            try:
                policy = Policy(options["policy"])
                storage.client.set_bucket_policy(
                    bucket_name, policy.bucket(bucket_name)
                )
            except minio.error.NoSuchBucket as e:
                raise CommandError(e.message)
