import json

import minio
import requests
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from minio_storage.policy import Policy
from minio_storage.storage import MinioMediaStorage, MinioStaticStorage, get_setting

from .utils import BaseTestMixin


class BucketTests(BaseTestMixin, TestCase):
    @override_settings(
        MINIO_STORAGE_MEDIA_BUCKET_NAME="inexistent",
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=False,
    )
    def test_media_storage_cannot_be_initialized_without_bucket(self):
        with self.assertRaises(OSError):
            MinioMediaStorage()

    @override_settings(
        MINIO_STORAGE_STATIC_BUCKET_NAME="inexistent",
        MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET=False,
    )
    def test_static_storage_cannot_be_initialized_without_bucket(self):
        with self.assertRaises(OSError):
            MinioStaticStorage()

    def test_get_setting_throws_early(self):
        with self.assertRaises(ImproperlyConfigured):
            get_setting("INEXISTENT_SETTING")

    @override_settings(
        MINIO_STORAGE_MEDIA_BUCKET_NAME="inexistent",
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=False,
        MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS=True,
    )
    def test_media_storage_ignore_bucket_check(self):
        MinioMediaStorage()

    @override_settings(
        MINIO_STORAGE_STATIC_BUCKET_NAME="inexistent",
        MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET=False,
        MINIO_STORAGE_ASSUME_STATIC_BUCKET_EXISTS=True,
    )
    def test_static_storage_ignore_bucket_check(self):
        MinioStaticStorage()


class BucketPolicyTests(BaseTestMixin, TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        self.obliterate_bucket(self.bucket_name("tests-media"))

    def assertPolicyEqual(self, first, second):
        """A stupid method to compare policies which is enough for this test"""

        def comparable(v):
            return sorted(json.dumps(v))

        def pretty(v):
            return json.dumps(v, sort_keys=True, indent=2)

        if comparable(first) != comparable(second):
            raise ValueError(
                f"not equal:\n\n ------{pretty(first)}\n\n ------{pretty(second)}"
            )

    @override_settings(
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=True,
        MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY=False,
    )
    def test_auto_create_no_policy(self):
        ms = MinioMediaStorage()
        with self.assertRaises(minio.error.NoSuchBucketPolicy):
            ms.client.get_bucket_policy(ms.bucket_name)

    @override_settings(
        MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY=True,
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=True,
    )
    def test_media_policy_auto_true(self):
        ms = MinioMediaStorage()
        self.maxDiff = 50000
        self.assertPolicyEqual(
            Policy.get.bucket(ms.bucket_name, json_encode=False),
            json.loads(ms.client.get_bucket_policy(ms.bucket_name)),
        )
        fn = ms.save("somefile", ContentFile(b"test"))
        self.assertEqual(ms.open(fn).read(), b"test")
        url = ms.url(fn)
        self.assertEqual(requests.get(url).status_code, 200)
        self.assertEqual(
            requests.get(f"{ms.client._endpoint_url}/{ms.bucket_name}").status_code, 403
        )

    @override_settings(
        MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY="GET_ONLY",
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=True,
    )
    def test_media_policy_get(self):
        ms = MinioMediaStorage()
        self.maxDiff = 50000
        self.assertPolicyEqual(
            Policy.get.bucket(ms.bucket_name, json_encode=False),
            json.loads(ms.client.get_bucket_policy(ms.bucket_name)),
        )
        fn = ms.save("somefile", ContentFile(b"test"))
        self.assertEqual(ms.open(fn).read(), b"test")
        self.assertEqual(requests.get(ms.url(fn)).status_code, 200)
        self.assertEqual(
            requests.get(f"{ms.client._endpoint_url}/{ms.bucket_name}").status_code, 403
        )

    @override_settings(
        MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY="WRITE_ONLY",
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=True,
    )
    def test_media_policy_write(self):
        ms = MinioMediaStorage()
        self.maxDiff = 50000
        self.assertPolicyEqual(
            Policy.write.bucket(ms.bucket_name, json_encode=False),
            json.loads(ms.client.get_bucket_policy(ms.bucket_name)),
        )
        fn = ms.save("somefile", ContentFile(b"test"))
        self.assertEqual(ms.open(fn).read(), b"test")
        self.assertEqual(requests.get(ms.url(fn)).status_code, 403)
        self.assertEqual(
            requests.get(f"{ms.client._endpoint_url}/{ms.bucket_name}").status_code, 403
        )

    @override_settings(
        MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY="READ_WRITE",
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=True,
    )
    def test_media_policy_rw(self):
        ms = MinioMediaStorage()
        self.maxDiff = 50000
        self.assertPolicyEqual(
            Policy.read_write.bucket(ms.bucket_name, json_encode=False),
            json.loads(ms.client.get_bucket_policy(ms.bucket_name)),
        )

    @override_settings(
        MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY=True,
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=True,
        MINIO_STORAGE_AUTO_CREATE_STATIC_POLICY=True,
        MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET=True,
    )
    def test_public_url_generation(self):
        media_storage = MinioMediaStorage()
        media_test_file_name = media_storage.save(
            "weird & ÜRΛ", ContentFile(b"irrelevant")
        )
        url = media_storage.url(media_test_file_name)
        res = requests.get(url)
        self.assertEqual(res.content, b"irrelevant")

        static_storage = MinioStaticStorage()
        static_test_file_name = static_storage.save(
            "weird & ÜRΛ", ContentFile(b"irrelevant")
        )
        url = static_storage.url(static_test_file_name)
        res = requests.get(url)
        self.assertEqual(res.content, b"irrelevant")
