from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from minio_storage.storage import MinioMediaStorage, MinioStaticStorage, get_setting

from .utils import BaseTestMixin


class BucketTests(BaseTestMixin, TestCase):
    @override_settings(
        MINIO_STORAGE_MEDIA_BUCKET_NAME="inexistent",
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=False,
    )
    def test_media_storage_cannot_be_initialized_without_bucket(self):
        with self.assertRaises(IOError):
            MinioMediaStorage()

    @override_settings(
        MINIO_STORAGE_STATIC_BUCKET_NAME="inexistent",
        MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET=False,
    )
    def test_static_storage_cannot_be_initialized_without_bucket(self):
        with self.assertRaises(IOError):
            MinioStaticStorage()

    def test_get_setting_throws_early(self):
        with self.assertRaises(ImproperlyConfigured):
            get_setting("INEXISTENT_SETTING")
