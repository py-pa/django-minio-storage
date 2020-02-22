import os

import requests
from django.conf import settings
from django.core.files.base import ContentFile, File
from django.test import TestCase, override_settings
from minio.error import InvalidAccessKeyId

from minio_storage.storage import MinioMediaStorage

from .utils import BaseTestMixin


@override_settings(
    MINIO_STORAGE_MEDIA_USE_PRESIGNED=True, MINIO_STORAGE_STATIC_USE_PRESIGNED=True
)
class UploadTests(BaseTestMixin, TestCase):
    def test_file_upload_success(self):
        self.media_storage.save("trivial.txt", ContentFile(b"12345"))

    @override_settings(
        MINIO_STORAGE_ACCESS_KEY="wrong_key", MINIO_STORAGE_SECRET_KEY="wrong_secret"
    )
    def test_file_upload_fail_incorrect_keys(self):
        with self.assertRaises(InvalidAccessKeyId):
            MinioMediaStorage()

    def test_two_files_with_the_same_name_can_be_uploaded(self):
        ivan = self.media_storage.save("pelican.txt", ContentFile(b"Ivan le Pelican"))
        jean = self.media_storage.save("pelican.txt", ContentFile(b"Jean le Pelican"))
        self.assertNotEqual(jean, ivan)

    def test_files_from_filesystem_are_uploaded_properly(self):
        f = File(open(os.path.join(settings.BASE_DIR, "watermelon-cat.jpg"), "br"))
        saved_file = self.media_storage.save("watermelon-cat.jpg", f)
        res = requests.get(self.media_storage.url(saved_file))
        self.assertAlmostEqual(
            round(res.content.__sizeof__() / 100), round(f.size / 100)
        )

    def test_files_are_uploaded_from_the_beginning(self):
        local_filename = os.path.join(settings.BASE_DIR, "watermelon-cat.jpg")
        f = open(local_filename, "br")
        f.seek(20000)
        saved_file = self.media_storage.save("watermelon-cat.jpg", f)
        file_size = os.stat(local_filename).st_size
        res = requests.get(self.media_storage.url(saved_file))
        self.assertAlmostEqual(
            round(res.content.__sizeof__() / 100), round(file_size / 100)
        )

    def test_files_cannot_be_open_in_write_mode(self):
        test_file = self.media_storage.save(
            "iomodetest.txt", ContentFile(b"should not change")
        )
        with self.assertRaises(NotImplementedError):
            self.media_storage.open(test_file, mode="bw")

    def test_files_seekable(self):
        self.media_storage.save("read_seek_test.txt", ContentFile(b"should not change"))

        f = self.media_storage.open("read_seek_test.txt", mode="br")
        f.seek(4)
        f.seek(0)

    def test_upload_and_get_back_file_with_funky_name(self):
        self.media_storage.save("áčďěščřžýŽŇůúť.txt", ContentFile(b"12345"))

    def test_uploaded_and_downloaded_file_sizes_match(self):
        pass

    def test_uploaded_files_end_up_in_the_right_bucket(self):
        pass

    def test_static_files_end_up_in_the_right_bucket(self):
        pass

    def test_upload_file_beggining_with_dot(self):
        self.media_storage.save(
            ".hidden_file", ContentFile(b"Not really, but whatever")
        )
        self.assertTrue(self.media_storage.exists(".hidden_file"))
        self.media_storage.delete(".hidden_file")
        self.assertFalse(self.media_storage.exists(".hidden_file"))

    def test_metadata(self):
        ivan = self.media_storage.save("pelican.txt", ContentFile(b"Ivan le Pelican"))
        res = self.media_storage.client.stat_object(
            self.media_storage.bucket_name, ivan
        )
        self.assertEqual(res.metadata, {"Content-Type": "text/plain"})


@override_settings(
    MINIO_STORAGE_MEDIA_OBJECT_METADATA={"Cache-Control": "max-age=1000"},
)
class TestDefaultObjectMetadata(BaseTestMixin, TestCase):
    def test_default_metadata(self):
        ivan = self.media_storage.save("pelican.txt", ContentFile(b"Ivan le Pelican"))
        res = self.media_storage.client.stat_object(
            self.media_storage.bucket_name, ivan
        )
        self.assertEqual(
            res.metadata,
            {"Cache-Control": "max-age=1000", "Content-Type": "text/plain"},
        )
