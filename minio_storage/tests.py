from minio_storage.storage import MinioMediaStorage, MinioStaticStorage, get_setting

from django.test import TestCase, override_settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from minio import Minio, ResponseError

import requests
import os
import io
import datetime
from unittest.mock import patch, MagicMock
from logging import getLogger

logger = getLogger(__name__)

ENDPOINT = "minio:9000"


@override_settings(
    MINIO_STORAGE_ENDPOINT=ENDPOINT,
    MINIO_STORAGE_ACCESS_KEY=os.environ["MINIO_STORAGE_ACCESS_KEY"],
    MINIO_STORAGE_SECRET_KEY=os.environ["MINIO_STORAGE_SECRET_KEY"],
    MINIO_STORAGE_MEDIA_BUCKET_NAME="tests-media",
    MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET=True,
    MINIO_STORAGE_AUTO_CREATE_STATIC_BUCKET=True,
    MINIO_STORAGE_STATIC_BUCKET_NAME="tests-static",
    MINIO_STORAGE_USE_HTTPS=False,
)
class MinioStorageTests(TestCase):
    def setUp(self):
        self.media_storage = MinioMediaStorage()
        self.static_storage = MinioStaticStorage()
        self.new_file = self.media_storage.save("a new & original file",
                                                io.BytesIO(b"yep"))

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

    def test_file_upload_does_not_throw(self):
        self.media_storage.save("trivial.txt", io.BytesIO(b"12345"))

    def test_two_files_with_the_same_name_can_be_uploaded(self):
        ivan = self.media_storage.save("pelican.txt",
                                       io.BytesIO(b"Ivan le Pelican"))
        jean = self.media_storage.save("pelican.txt",
                                       io.BytesIO(b"Jean le Pelican"))
        self.assertNotEqual(jean, ivan)


    @patch("minio.Minio.put_object", side_effect=ResponseError(MagicMock()))
    def test_file_upload_throws_on_failure(self, mock):
        with self.assertRaises(IOError):
            self.media_storage.save("meh", io.BytesIO(b"meh"))

    def test_file_removal(self):
        test_file = self.media_storage.save("should_be_removed.txt",
                                            io.BytesIO(b"meh"))
        self.media_storage.delete(test_file)
        self.assertFalse(self.media_storage.exists(test_file))

    def test_delete_of_non_existent_throws(self):
        with self.assertRaises(IOError):
            self.media_storage.delete("i don't even exist")

    def test_url_generation(self):
        test_file = self.media_storage.save("weird & ÜRΛ",
                                            io.BytesIO(b"irrelevant"))
        url = self.media_storage.url(test_file)
        res = requests.get(url)
        self.assertEqual(res.content, b"irrelevant")

    def test_url_of_non_existent_throws(self):
        with self.assertRaises(IOError):
            self.media_storage.url("this does not exist")

    def test_file_stat(self):
        pass

    def test_file_size(self):
        test_file = self.media_storage.save("sizetest.txt",
                                            io.BytesIO(b"1234"))
        self.assertEqual(4, self.media_storage.size(test_file))

    def test_size_of_non_existent_throws(self):
        test_file = self.media_storage.save("sizetest.txt",
                                            io.BytesIO(b"1234"))
        self.media_storage.delete(test_file)
        with self.assertRaises(IOError):
            self.media_storage.size(test_file)

    def test_modified_time(self):
        self.assertIsInstance(self.media_storage.modified_time(self.new_file),
                              datetime.datetime)

    def test_accessed_time(self):
        self.assertIsInstance(self.media_storage.accessed_time(self.new_file),
                              datetime.datetime)

    def test_created_time(self):
        self.assertIsInstance(self.media_storage.created_time(self.new_file),
                              datetime.datetime)

    def test_modified_time_of_non_existent_throws(self):
        with self.assertRaises(IOError):
            self.media_storage.modified_time("nonexistent.jpg")

    def test_files_cannot_be_open_in_write_mode(self):
        test_file = self.media_storage.save("iomodetest.txt",
                                            io.BytesIO(b"should not change"))
        with self.assertRaises(NotImplementedError):
            self.media_storage.open(test_file, mode="bw")

    def test_list_dir_base(self):
        test_dir = self.media_storage.listdir("/")
        files = [elem for elem in test_dir]
        self.assertIsInstance(files, list)
        self.assertGreaterEqual(len(files), 1)

    @patch("minio.Minio.list_objects", side_effect=ResponseError(MagicMock()))
    def test_list_dir_throws_on_failure(self, mock):
        with self.assertRaises(IOError):
            self.media_storage.listdir("")

    def test_file_exists(self):
        existent = self.media_storage.save("existent.txt", io.BytesIO(b"meh"))
        self.assertTrue(self.media_storage.exists(existent))

    def test_file_exists_failure(self):
        self.assertFalse(self.media_storage.exists("nonexistent.txt"))

    @patch("minio.Minio.stat_object", side_effect=ResponseError(MagicMock()))
    def test_file_exists_can_throw(self, mock):
        with self.assertRaises(IOError):
            self.media_storage.exists("peu importe")

    def test_opening_non_existing_file_raises_exception(self):
        with self.assertRaises(IOError):
            self.media_storage.open("this does not exist")

    def test_upload_and_get_back_file_with_funky_name(self):
        pass

    def test_uploaded_and_downloaded_file_sizes_match(self):
        pass

    def test_uploaded_files_end_up_in_the_right_bucket(self):
        pass

    def test_static_files_end_up_in_the_right_bucket(self):
        pass

    def tearDown(self):
        client = Minio(endpoint=get_setting("MINIO_STORAGE_ENDPOINT"),
                       access_key=get_setting("MINIO_STORAGE_ACCESS_KEY"),
                       secret_key=get_setting("MINIO_STORAGE_SECRET_KEY"),
                       secure=get_setting("MINIO_STORAGE_USE_HTTPS"))

        def obliterate_bucket(name):
            for obj in client.list_objects(name, ""):
                client.remove_object(name, obj.object_name)
            for obj in client.list_incomplete_uploads(name, ""):  # pragma: no cover
                client.remove_incomplete_upload(name, obj.objectname)
            client.remove_bucket(name)

        obliterate_bucket("tests-media")
        obliterate_bucket("tests-static")
