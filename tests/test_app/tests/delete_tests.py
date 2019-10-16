from django.conf import settings
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone

from .utils import BaseTestMixin


class DeleteTests(BaseTestMixin, TestCase):
    def test_file_removal_success(self):
        test_file = self.media_storage.save(
            "should_be_removed.txt", ContentFile(b"meh")
        )
        self.media_storage.delete(test_file)
        self.assertFalse(self.media_storage.exists(test_file))


@override_settings(
    MINIO_STORAGE_MEDIA_BACKUP_BUCKET=settings.MINIO_STORAGE_MEDIA_BUCKET_NAME
)
@override_settings(MINIO_STORAGE_MEDIA_BACKUP_FORMAT="Recycle Bin/%Y-%m-%d/")
class BackupOnDeleteTests(BaseTestMixin, TestCase):
    def test_backup_on_file_removal(self):
        test_file = self.media_storage.save(
            "should_be_removed.txt", ContentFile(b"meh")
        )
        self.media_storage.delete(test_file)
        now = timezone.now()
        removed_filename = now.strftime("Recycle Bin/%Y-%m-%d/should_be_removed.txt")
        self.assertTrue(self.media_storage.exists(removed_filename))
        self.assertFalse(self.media_storage.exists(test_file))

    def test_no_backups_for_static_files_by_default(self):
        test_file = self.static_storage.save(
            "should_be_removed.txt", ContentFile(b"meh")
        )
        self.static_storage.delete(test_file)
        now = timezone.now()
        removed_filename = now.strftime("Recycle Bin/%Y-%m-%d/should_be_removed.txt")
        self.assertFalse(self.static_storage.exists(removed_filename))
        self.assertFalse(self.static_storage.exists(test_file))
