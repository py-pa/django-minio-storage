# encoding: utf-8
from __future__ import unicode_literals

from django.core.files.base import ContentFile
from minio import Minio
from minio_storage.storage import (MinioMediaStorage, MinioStaticStorage,
                                   get_setting)


class BaseTestMixin:

    def setUp(self):
        self.media_storage = MinioMediaStorage()
        self.static_storage = MinioStaticStorage()
        self.new_file = self.media_storage.save("test-file",
                                                ContentFile(b"yep"))
        self.second_file = self.media_storage.save("test-file",
                                                ContentFile(b"nope"))

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
