# encoding: utf-8
from __future__ import unicode_literals

from django.core.files.base import ContentFile
from django.test import TestCase

from .utils import BaseTestMixin


class DeleteTests(BaseTestMixin, TestCase):

    def test_file_removal_success(self):
        test_file = self.media_storage.save("should_be_removed.txt",
                                            ContentFile(b"meh"))
        self.media_storage.delete(test_file)
        self.assertFalse(self.media_storage.exists(test_file))
