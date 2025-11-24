from django.test import TestCase, override_settings

from minio_storage.storage import MinioMediaStorage
from tests.test_app.tests.utils import BaseTestMixin


class SettingsTests(BaseTestMixin, TestCase):
    @override_settings(
        MINIO_STORAGE_REGION="eu-central-666",
    )
    def test_settings_with_region(self):
        ms = MinioMediaStorage()
        region = ms.client._get_region(bucket_name=self.bucket_name("tests-media"))
        self.assertEqual(region, "eu-central-666")

    def test_settings_without_region(self):
        ms = MinioMediaStorage()
        region = ms.client._get_region(bucket_name=self.bucket_name("tests-media"))
        self.assertEqual(region, "us-east-1")
