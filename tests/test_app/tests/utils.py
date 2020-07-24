import hashlib
import os
import warnings

from django.core.files.base import ContentFile
from minio import Minio

from minio_storage.storage import MinioMediaStorage, MinioStaticStorage, get_setting

warnings.simplefilter("default")
warnings.filterwarnings(
    "ignore", message="This usage is deprecated, please use pytest.* instead"
)


warnings.simplefilter("ignore", ResourceWarning)


def bucket_name(name):
    env_name = os.getenv("TOX_ENVNAME", "").encode("utf-8")
    env_hash = hashlib.md5(env_name).hexdigest()
    return "".join([name, env_hash])


class BaseTestMixin:
    @staticmethod
    def bucket_name(name):
        return bucket_name(name)

    def setUp(self):
        self.media_storage = MinioMediaStorage()
        self.static_storage = MinioStaticStorage()
        self.new_file = self.media_storage.save("test-file", ContentFile(b"yep"))
        self.second_file = self.media_storage.save("test-file", ContentFile(b"nope"))

    def tearDown(self):
        client = self.minio_client()
        self.obliterate_bucket(self.bucket_name("tests-media"), client=client)
        self.obliterate_bucket(self.bucket_name("tests-static"), client=client)

    def minio_client(self):
        minio_client = Minio(
            endpoint=get_setting("MINIO_STORAGE_ENDPOINT"),
            access_key=get_setting("MINIO_STORAGE_ACCESS_KEY"),
            secret_key=get_setting("MINIO_STORAGE_SECRET_KEY"),
            secure=get_setting("MINIO_STORAGE_USE_HTTPS"),
        )
        return minio_client

    def obliterate_bucket(self, name, client=None):
        if client is None:
            client = self.minio_client()

        for obj in client.list_objects(name, "", True):
            client.remove_object(name, obj.object_name)
        for obj in client.list_incomplete_uploads(name, ""):  # pragma: no cover  # noqa
            client.remove_incomplete_upload(name, obj.objectname)
        client.remove_bucket(name)
