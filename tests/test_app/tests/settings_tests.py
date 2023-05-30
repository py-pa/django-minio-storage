from django.test import TestCase, override_settings

from minio_storage.storage import MinioMediaStorage


class SettingsTests(TestCase):
    @override_settings(
        MINIO_STORAGE_REGION="eu-central-666",
        MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET=True,
        MINIO_STORAGE_STATIC_BUCKET_NAME="settings-test",
    )
    def test_settings_region(self):
        ms = MinioMediaStorage()
        region = ms.client._get_region("settings-test", None)
        self.assertEqual(region, "eu-central-666")
