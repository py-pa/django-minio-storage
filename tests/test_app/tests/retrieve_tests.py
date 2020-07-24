import datetime
import io
import os
import unittest

import requests
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from freezegun import freeze_time
from minio.error import NoSuchKey

from minio_storage.errors import MinIOError
from minio_storage.storage import MinioMediaStorage

from .utils import BaseTestMixin


@override_settings(
    MINIO_STORAGE_MEDIA_USE_PRESIGNED=True, MINIO_STORAGE_STATIC_USE_PRESIGNED=True
)
class RetrieveTestsWithRestrictedBucket(BaseTestMixin, TestCase):
    def test_presigned_url_generation(self):
        media_test_file_name = self.media_storage.save(
            "weird & ÜRΛ", ContentFile(b"irrelevant")
        )
        url = self.media_storage.url(media_test_file_name)
        res = requests.get(url)
        self.assertEqual(res.content, b"irrelevant")

        static_test_file_name = self.static_storage.save(
            "weird & ÜRΛ", ContentFile(b"irrelevant")
        )
        url = self.static_storage.url(static_test_file_name)
        res = requests.get(url)
        self.assertEqual(res.content, b"irrelevant")

    def test_url_of_non_existent_object(self):
        self.media_storage.url("this does not exist")

    def test_file_size(self):
        test_file = self.media_storage.save("sizetest.txt", ContentFile(b"1234"))
        self.assertEqual(4, self.media_storage.size(test_file))

    def test_size_of_non_existent_throws(self):
        test_file = self.media_storage.save("sizetest.txt", ContentFile(b"1234"))
        self.media_storage.delete(test_file)
        with self.assertRaises(NoSuchKey):
            self.media_storage.size(test_file)

    def test_modified_time(self):
        self.assertIsInstance(
            self.media_storage.modified_time(self.new_file), datetime.datetime
        )

    def test_accessed_time(self):
        self.assertIsInstance(
            self.media_storage.accessed_time(self.new_file), datetime.datetime
        )

    def test_created_time(self):
        self.assertIsInstance(
            self.media_storage.created_time(self.new_file), datetime.datetime
        )

    def test_modified_time_of_non_existent_throws(self):
        with self.assertRaises(NoSuchKey):
            self.media_storage.modified_time("nonexistent.jpg")

    def _listdir_root(self, root):
        self.media_storage.save("dir1/file2.txt", ContentFile(b"meh"))
        test_dir = self.media_storage.listdir(root)
        (dirs, files) = test_dir
        self.assertEqual(dirs, ["dir1"])
        self.assertEqual(files, sorted([self.new_file, self.second_file]))
        self.assertEqual(len(files), 2)
        self.assertEqual(len(test_dir), 2)

    def test_listdir_emptystr(self):
        self._listdir_root("")

    def test_listdir_dot(self):
        self._listdir_root(".")

    def test_listdir_none(self):
        self._listdir_root(None)

    def test_listdir_slash(self):
        self._listdir_root("/")

    def _listdir_sub(self, path):
        self.media_storage.save("dir/file.txt", ContentFile(b"meh"))
        self.media_storage.save("dir/file2.txt", ContentFile(b"meh"))
        self.media_storage.save("dir/dir3/file3.txt", ContentFile(b"meh"))
        dirs, files = self.media_storage.listdir("dir/")
        self.assertEqual((dirs, files), (["dir3"], ["file.txt", "file2.txt"]))

    def test_listdir_subdir_slash(self):
        self._listdir_sub("dir/")

    def test_listdir_subdir_noslash(self):
        self._listdir_sub("dir")

    def test_list_nonexist(self):
        test_dir = self.media_storage.listdir("nonexist")
        self.assertEqual(test_dir, ([], []))

    def test_list_prefix(self):
        self.media_storage.save("dir/file.txt", ContentFile(b"meh"))
        test_dir = self.media_storage.listdir("di")
        self.assertEqual(test_dir, ([], []))

    def test_file_exists(self):
        existent = self.media_storage.save("existent.txt", ContentFile(b"meh"))
        self.assertTrue(self.media_storage.exists(existent))

    def test_file_exists_failure(self):
        self.assertFalse(self.media_storage.exists("nonexistent.txt"))

    @unittest.skip("Skipping this test because undecided if it should raise exception")
    def test_opening_non_existing_file_raises_oserror(self):
        with self.assertRaises(OSError):
            self.media_storage.open("this does not exist")

    @unittest.skip("Skipping this test because undecided if it should raise exception")
    def test_opening_non_existing_file_raises_minioerror(self):
        with self.assertRaises(MinIOError):
            self.media_storage.open("this does not exist")
        try:
            self.media_storage.open("this does not exist")
        except MinIOError as e:
            assert e.cause.__class__ == NoSuchKey

    def test_file_names_are_properly_sanitized(self):
        self.media_storage.save("./meh22222.txt", io.BytesIO(b"stuff"))

    def test_url_max_age(self):
        url = self.media_storage.url(
            "test-file", max_age=datetime.timedelta(seconds=10)
        )
        self.assertEqual(requests.get(url).status_code, 200)

    def test_max_age_too_old(self):
        with freeze_time(-datetime.timedelta(seconds=10)):
            url = self.media_storage.url(
                "test-file", max_age=datetime.timedelta(seconds=10)
            )
        self.assertEqual(requests.get(url).status_code, 403)

    def test_no_file(self):
        url = self.media_storage.url("no-file", max_age=datetime.timedelta(seconds=10))
        self.assertEqual(requests.get(url).status_code, 404)

    def test_max_age_no_file(self):
        with freeze_time(-datetime.timedelta(seconds=10)):
            url = self.media_storage.url(
                "no-file", max_age=datetime.timedelta(seconds=10)
            )
        self.assertEqual(requests.get(url).status_code, 403)


class URLTests(TestCase):
    @override_settings(
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_URL=None,
        MINIO_STORAGE_MEDIA_BUCKET_NAME="foo",
    )
    def test_no_base_url(self):
        endpoint = os.getenv("MINIO_STORAGE_ENDPOINT", "minio:9000")
        assert endpoint != ""
        media_storage = MinioMediaStorage()
        url = media_storage.url("22")
        self.assertEqual(url, f"http://{endpoint}/foo/22")

    @override_settings(
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_URL=None,
        MINIO_STORAGE_MEDIA_BUCKET_NAME="foo",
    )
    def test_no_base_url_subpath(self):
        endpoint = os.getenv("MINIO_STORAGE_ENDPOINT", "minio:9000")
        assert endpoint != ""
        media_storage = MinioMediaStorage()
        name = "23/23/aaa/bbb/22"
        url = media_storage.url(name)
        self.assertEqual(url, f"http://{endpoint}/foo/23/23/aaa/bbb/22")

    @override_settings(
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=True,
        MINIO_STORAGE_MEDIA_URL=None,
        MINIO_STORAGE_MEDIA_BUCKET_NAME="foo",
    )
    def test_presigned_no_base_url(self):
        endpoint = os.getenv("MINIO_STORAGE_ENDPOINT", "minio:9000")
        assert endpoint != ""
        media_storage = MinioMediaStorage()
        url = media_storage.url("22")
        self.assertRegex(url, rf"^http://{endpoint}/foo/22\?")

    @override_settings(
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_URL="https://example23.com/foo",
        MINIO_STORAGE_MEDIA_BUCKET_NAME="bar",
    )
    def test_base_url(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url("1")
        self.assertEqual(url, "https://example23.com/foo/1")

    @override_settings(
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_URL="https://example23.com/foo",
        MINIO_STORAGE_MEDIA_BUCKET_NAME="bar",
    )
    def test_base_url_subpath(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url("1/2/3/4")
        self.assertEqual(url, "https://example23.com/foo/1/2/3/4")

    @override_settings(
        MINIO_STORAGE_MEDIA_URL="http://example11.com/foo",
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=True,
        MINIO_STORAGE_MEDIA_BUCKET_NAME="bar",
    )
    def test_presigned_base_url(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url("1")
        self.assertIn("X-Amz-Signature", url)
        self.assertRegex(url, r"^http://example11.com/foo/1\?")

    @override_settings(
        MINIO_STORAGE_MEDIA_URL="http://example11.com/foo",
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=True,
        MINIO_STORAGE_MEDIA_BUCKET_NAME="bar",
    )
    def test_presigned_base_url_subpath(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url("1/555/666/777")
        self.assertIn("X-Amz-Signature", url)
        self.assertRegex(url, r"^http://example11.com/foo/1/555/666/777\?")

    BASE = "http://base/url"
    NAME = "Bö/ &öl@:/E"
    ENCODED = "B%C3%B6/%20%26%C3%B6l%40%3A/E"

    @override_settings(
        MINIO_STORAGE_MEDIA_URL=None,
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_BUCKET_NAME="encoding",
    )
    def test_quote_url(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url(self.NAME)
        self.assertTrue(url.endswith(self.ENCODED))
        self.assertTrue(len(url) > len(self.ENCODED))

    @override_settings(
        MINIO_STORAGE_MEDIA_URL=BASE,
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=False,
        MINIO_STORAGE_MEDIA_BUCKET_NAME="encoding",
    )
    def test_quote_base_url(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url(self.NAME)
        self.assertEqual(url, f"{self.BASE}/{self.ENCODED}")

    @override_settings(
        MINIO_STORAGE_MEDIA_URL=BASE,
        MINIO_STORAGE_MEDIA_USE_PRESIGNED=True,
        MINIO_STORAGE_MEDIA_BUCKET_NAME="encoding",
    )
    def test_quote_base_url_presigned(self):
        media_storage = MinioMediaStorage()
        url = media_storage.url(self.NAME)
        prefix = f"{self.BASE}/{self.ENCODED}"
        self.assertTrue(url.startswith(prefix))
        self.assertTrue(len(url) > len(prefix))
