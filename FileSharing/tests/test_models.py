from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from ..models import FileModel, FilePermissionModel
from django.db.utils import DataError

User = get_user_model()


class FileModelTestCase(TestCase):

    def setUp(self):
        self.file = FileModel.objects.create(
            original_filename="test_file.txt", size=1024, file_extension="txt"
        )

    def test_create_file_model(self):
        self.assertIsInstance(self.file, FileModel)
        self.assertEqual(self.file.original_filename, "test_file.txt")

    def test_retrieve_file_model(self):
        file = FileModel.objects.get(id=self.file.id)
        self.assertEqual(file.original_filename, "test_file.txt")
        self.assertEqual(file.size, 1024)
        self.assertEqual(file.file_extension, "txt")

    def test_update_file_model(self):
        self.file.original_filename = "updated_file.txt"
        self.file.save()
        self.file.refresh_from_db()
        self.assertEqual(self.file.original_filename, "updated_file.txt")

    def test_delete_file_model(self):
        file_id = self.file.id
        self.file.delete()
        with self.assertRaises(FileModel.DoesNotExist):
            FileModel.objects.get(id=file_id)

    def test_file_model_str(self):
        self.assertEqual(str(self.file), "test_file.txt")

    def test_file_extension_constraint(self):
        self.file.file_extension = "doc"
        self.file.save()
        self.assertEqual(self.file.file_extension, "doc")

    def test_original_filename_max_length(self):
        long_filename = "a" * 256
        with self.assertRaises(DataError):
            FileModel.objects.create(
                original_filename=long_filename, size=1024, file_extension="txt"
            )

    def test_size_positive_integer(self):
        self.file.size = -1
        with self.assertRaises(ValidationError):
            self.file.full_clean()

    def test_upload_date_auto_now_add(self):
        self.assertIsNotNone(self.file.upload_date)

    def test_id_is_unique(self):
        file = FileModel.objects.create(
            original_filename="another_file.txt", size=2048, file_extension="pdf"
        )
        self.assertNotEqual(self.file.id, file.id)


class FilePermissionModelTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.file = FileModel.objects.create(
            original_filename="test_file.txt", size=1024, file_extension="txt"
        )
        self.permission = FilePermissionModel.objects.create(
            file=self.file, user=self.user, permission="R"
        )

    def test_create_file_permission_model(self):
        self.assertIsInstance(self.permission, FilePermissionModel)
        self.assertEqual(self.permission.permission, "R")

    def test_retrieve_file_permission_model(self):
        permission = FilePermissionModel.objects.get(id=self.permission.id)
        self.assertEqual(permission.permission, "R")

    def test_update_file_permission_model(self):
        self.permission.permission = "F"
        self.permission.save()
        self.permission.refresh_from_db()
        self.assertEqual(self.permission.permission, "F")

    def test_delete_file_permission_model(self):
        permission_id = self.permission.id
        self.permission.delete()
        with self.assertRaises(FilePermissionModel.DoesNotExist):
            FilePermissionModel.objects.get(id=permission_id)

    def test_file_permission_model_str(self):
        self.assertEqual(str(self.permission), f"{self.user} - {self.file}")

    def test_permission_field_choices(self):
        with self.assertRaises(ValidationError):
            FilePermissionModel.objects.create(
                file=self.file, user=self.user, permission="X"
            ).full_clean()

    def test_unique_together_constraint(self):
        with self.assertRaises(ValidationError):
            FilePermissionModel.objects.create(
                file=self.file, user=self.user, permission="W"
            ).full_clean()

    def test_related_name_for_file(self):
        self.assertEqual(self.file.file_permissions.count(), 1)

    def test_related_name_for_user(self):
        self.assertEqual(self.user.file_permissions.count(), 1)

    def test_created_at_auto_now_add(self):
        self.assertIsNotNone(self.permission.created_at)
