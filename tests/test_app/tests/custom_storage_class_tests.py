import io
import os
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils.deconstruct import deconstructible
from minio_storage.files import ReadOnlyMinioObjectFile
from minio_storage.storage import (
    MinioStorage,
    create_minio_client_from_settings,
    get_setting,
)

from .utils import BaseTestMixin


@deconstructible
class SecretStorage(MinioStorage):
    """The SecretStorage MinioStorage subclass can be used directly, as a storage in
    settings.DEFAULT_FILE_STORAGE or after instantiated used individually on any django
    FileField:

    from django.db import models

    ss = SecretStorage(bucket_name='invoices')

    class Invoice(models.Model):
        ...
        pdf = models.FileField(storage=ss)

    """

    # We can set a new default File class implementation that will be used here
    file_class = ReadOnlyMinioObjectFile

    def __init__(self, bucket_name=None):

        # we can create the minio client ourselves or use
        # create_minio_client_from_settings convinience function while providing it with
        # extra args.
        client = create_minio_client_from_settings(minio_kwargs={"region": "us-east-1"})

        # or use our own Django setting
        if bucket_name is None:
            bucket_name = get_setting("SECRET_BUCKET_NAME")

        # Run the super constructor and make a choice to only use presigned urls with
        # this bucket so that we can keep files more private here than how media files
        # usually are public readable.
        super().__init__(
            client, bucket_name, auto_create_bucket=True, presign_urls=True
        )


class CustomStorageTests(BaseTestMixin, TestCase):
    @override_settings(SECRET_BUCKET_NAME="my-secret-bucket")
    def test_custom_storage(self):
        storage = SecretStorage()
        storage_filename = storage.save("secret.txt", ContentFile(b"abcd"))

        # create a temporary workspace directory
        with tempfile.TemporaryDirectory() as workspace:

            # a filename to use for the file inside the working directory.
            filename = os.path.join(workspace, "secret.txt")

            # Open a stream with the minio file objenct and the temporary file.
            with open(filename, "wb") as out_file, storage.open(
                storage_filename
            ) as storage_file:

                # copy the stream from the http stream to the out_file
                shutil.copyfileobj(storage_file.file, out_file)

                with self.assertRaises(io.UnsupportedOperation):
                    storage_file.file.seek()

            workspace_files = os.listdir(workspace)
            print(workspace_files)  # prints: ['secret.txt']

            #
            # Process the file with external tools or something....
            #  ...
            #

            with open(filename, "rb") as f:
                self.assertEqual(f.read(), b"abcd")
