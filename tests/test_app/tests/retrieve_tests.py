# encoding: utf-8
from __future__ import unicode_literals

import datetime
import io

import requests
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from minio.error import NoSuchKey
from minio.policy import Policy

from minio_storage.errors import MinIOError
from minio_storage.storage import MinioMediaStorage, MinioStaticStorage

from .utils import BaseTestMixin


@override_settings(
    MINIO_STORAGE_MEDIA_USE_PRESIGNED=True,
    MINIO_STORAGE_STATIC_USE_PRESIGNED=True,
)
class RetrieveTestsWithRestrictedBucket(BaseTestMixin, TestCase):

    def test_presigned_url_generation(self):
        media_test_file_name = self.media_storage.save(
            u"weird & ÜRΛ", ContentFile(b"irrelevant"))
        url = self.media_storage.url(media_test_file_name)
        res = requests.get(url)
        self.assertEqual(res.content, b"irrelevant")

        static_test_file_name = self.static_storage.save(
            u"weird & ÜRΛ", ContentFile(b"irrelevant"))
        url = self.static_storage.url(static_test_file_name)
        res = requests.get(url)
        self.assertEqual(res.content, b"irrelevant")

    def test_url_of_non_existent_object(self):
        self.media_storage.url("this does not exist")

    def test_file_size(self):
        test_file = self.media_storage.save("sizetest.txt",
                                            ContentFile(b"1234"))
        self.assertEqual(4, self.media_storage.size(test_file))

    # TODO - temporarily diapbled due to
    # https://github.com/minio/minio-py/issues/514
    #
    # def test_size_of_non_existent_throws(self):
    #     test_file = self.media_storage.save("sizetest.txt",
    #                                         ContentFile(b"1234"))
    #     self.media_storage.delete(test_file)
    #     with self.assertRaises(NoSuchKey):
    #         self.media_storage.size(test_file)

    def test_modified_time(self):
        self.assertIsInstance(self.media_storage.modified_time(self.new_file),
                              datetime.datetime)

    def test_accessed_time(self):
        self.assertIsInstance(self.media_storage.accessed_time(self.new_file),
                              datetime.datetime)

    def test_created_time(self):
        self.assertIsInstance(self.media_storage.created_time(self.new_file),
                              datetime.datetime)

    # TODO - temporarily diapbled due to
    # https://github.com/minio/minio-py/issues/514
    #
    # def test_modified_time_of_non_existent_throws(self):
    #     with self.assertRaises(NoSuchKey):
    #         self.media_storage.modified_time("nonexistent.jpg")

    def test_list_dir_base(self):
        # Pre-condition
        self.assertIsNotNone(self.new_file)

        test_dir = self.media_storage.listdir(None)
        files = [elem for elem in test_dir]
        self.assertIsInstance(files, list)
        self.assertGreaterEqual(len(files), 1)

    def test_file_exists(self):
        existent = self.media_storage.save("existent.txt", ContentFile(b"meh"))
        self.assertTrue(self.media_storage.exists(existent))

    def test_file_exists_failure(self):
        self.assertFalse(self.media_storage.exists("nonexistent.txt"))

    def test_opening_non_existing_file_raises_ioerror(self):
        with self.assertRaises(IOError):
            self.media_storage.open("this does not exist")

    def test_opening_non_existing_file_raises_minioerror(self):
        with self.assertRaises(MinIOError):
            self.media_storage.open("this does not exist")
        try:
            self.media_storage.open("this does not exist")
        except MinIOError as e:
            assert e.cause.__class__ == NoSuchKey

    def test_file_names_are_properly_sanitized(self):
        self.media_storage.save("./meh22222.txt", io.BytesIO(b"stuff"))


class URLTests(TestCase):

    @override_settings(
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_URL=None,
        MINIO_STORAGE_MEDIA_BUCKET_NAME='foo',
    )
    def test_no_base_url(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url("22")
        self.assertEqual(url, 'http://localhost:9000/foo/22')

    @override_settings(
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_URL=None,
        MINIO_STORAGE_MEDIA_BUCKET_NAME='foo',
    )
    def test_no_base_url_subpath(self):
        media_storage = MinioMediaStorage()
        name = "23/23/aaa/bbb/22"
        url = media_storage.url(name)
        self.assertEqual(url, 'http://localhost:9000/foo/23/23/aaa/bbb/22')

    @override_settings(
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_URL='https://example23.com/foo',
        MINIO_STORAGE_MEDIA_BUCKET_NAME='bar',
    )
    def test_base_url(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url("1")
        self.assertEqual(url, 'https://example23.com/foo/1')

    @override_settings(
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_URL='https://example23.com/foo',
        MINIO_STORAGE_MEDIA_BUCKET_NAME='bar',
    )
    def test_base_url_subpath(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url("1/2/3/4")
        self.assertEqual(url, 'https://example23.com/foo/1/2/3/4')

    @override_settings(
        MINIO_STORAGE_MEDIA_URL='http://example11.com/foo',
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=True,
        MINIO_STORAGE_MEDIA_BUCKET_NAME='bar',
    )
    def test_presigned_base_url(self):
        # The url generated here probably doenst work in a real situation
        media_storage = MinioMediaStorage()
        url = media_storage.url("1")
        self.assertIn('X-Amz-Signature', url)
        self.assertIn("http://example11.com/foo", url)

    @override_settings(
        MINIO_STORAGE_MEDIA_URL='http://example11.com/foo',
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=True,
        MINIO_STORAGE_MEDIA_BUCKET_NAME='bar',
    )
    def test_presigned_base_url_subpath(self):
        # The url generated here probably doenst work in a real situation
        media_storage = MinioMediaStorage()
        name = "1/555/666/777"
        url = media_storage.url(name)
        self.assertIn('X-Amz-Signature', url)
        self.assertIn("http://example11.com/foo", url)
        self.assertIn(name, url)


class RetrieveTestsWithPublicBucket(BaseTestMixin, TestCase):

    def setUp(self):
        self.media_storage = MinioMediaStorage()
        self.static_storage = MinioStaticStorage()
        self.new_file = self.media_storage.save("test-file",
                                                ContentFile(b"yep"))
        self.media_storage.client.set_bucket_policy(
            self.media_storage.bucket_name, '', Policy.READ_WRITE)
        self.static_storage.client.set_bucket_policy(
            self.static_storage.bucket_name, '', Policy.READ_WRITE)

    def test_public_url_generation(self):
        media_test_file_name = self.media_storage.save(
            u"weird & ÜRΛ", ContentFile(b"irrelevant"))
        url = self.media_storage.url(media_test_file_name)
        res = requests.get(url)
        self.assertEqual(res.content, b"irrelevant")

        static_test_file_name = self.static_storage.save(
            u"weird & ÜRΛ", ContentFile(b"irrelevant"))
        url = self.static_storage.url(static_test_file_name)
        res = requests.get(url)
        self.assertEqual(res.content, b"irrelevant")
