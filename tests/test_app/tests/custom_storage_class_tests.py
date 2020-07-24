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
from .utils import bucket_name as create_test_bucket_name


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

    # We can set a new default File class implementation that will be used here because
    # we want to stream the data directly from minio. Imagine that we need to process
    # large files where we don't want to waste time/ram/disk space on  writing the file
    # to disk two times before processing it.
    #
    file_class = ReadOnlyMinioObjectFile

    def __init__(self, bucket_name=None):

        # we can create the minio client ourselves or use
        # create_minio_client_from_settings convinience function while providing it with
        # extra args.
        #
        client = create_minio_client_from_settings(minio_kwargs={"region": "us-east-1"})

        # or use our own Django setting
        #
        if bucket_name is None:
            bucket_name = get_setting("SECRET_BUCKET_NAME")

        # Run the super constructor and make a choice to only use presigned urls with
        # this bucket so that we can keep files more private here than how media files
        # usually are public readable.
        #
        super().__init__(
            client,
            bucket_name,
            auto_create_bucket=True,
            auto_create_policy=False,
            presign_urls=True,
        )


class CustomStorageTests(BaseTestMixin, TestCase):
    @override_settings(SECRET_BUCKET_NAME=create_test_bucket_name("my-secret-bucket"))
    def test_custom_storage(self):
        # Instansiate a storage class and put a file in it so that we have something to
        # work with.
        #
        storage = SecretStorage()
        storage_filename = storage.save("secret.txt", ContentFile(b"abcd"))

        # Create a temporary workspace directory.
        #
        # It's importat that this directory is deleted after we are done so we use the
        # with statement here.
        #
        with tempfile.TemporaryDirectory() as workspace:

            # A filename to use for the file inside the working directory.
            #
            filename = os.path.join(workspace, "secret.txt")

            # Open a stream with the minio file objenct and the temporary file.
            #
            # We might be processing a lot of files in a loop here so we are going top
            # use the with statement to ensure that both the input stream and output
            # files are closed after the copying is done.
            #
            with open(filename, "wb") as out_file, storage.open(
                storage_filename
            ) as storage_file:

                # Copy the stream from the http stream to the out_file
                #
                shutil.copyfileobj(storage_file.file, out_file)

                #
                # We are not using the ReadOnlyMinioObjectFile type so we can't seek in
                # it.
                #
                with self.assertRaises(io.UnsupportedOperation):
                    storage_file.file.seek()

            workspace_files = os.listdir(workspace)
            print(workspace_files)  # prints: ['secret.txt']

            #
            # Process the file with external tools or something....
            #
            # For the purpouse of the example test we just check that the contents of
            # the file is what we wrote in the beginning of the test.
            #
            with open(filename, "rb") as f:
                self.assertEqual(f.read(), b"abcd")

        #
        # Clean up after the test
        #
        storage.delete(storage_filename)

        #
        # use the minio client directly to also remove bucket
        #
        storage.client.remove_bucket(storage.bucket_name)
