import uuid
from django.db import models


def user_directory_path(instance, filename):
    return f"user_{instance.owner.id}/{filename}"


class FileModel(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    original_filename = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    file_extension = models.CharField(max_length=20)

    class Meta:
        db_table = "files"
        verbose_name = "File"
        verbose_name_plural = "Files"

    def __str__(self):
        return self.original_filename


class FilePermissionModel(models.Model):
    PERMISSION_CHOICES = [
        ("R", "Read Permission"),
        ("F", "Full Permission"),
    ]

    file = models.ForeignKey(
        FileModel, on_delete=models.CASCADE, related_name="file_permissions"
    )
    user = models.ForeignKey(
        "accounts.UserModel", on_delete=models.CASCADE, related_name="file_permissions"
    )
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "file_permissions"
        unique_together = ("file", "user")
        verbose_name = "File Permission"
        verbose_name_plural = "File Permissions"

    def __str__(self):
        return f"{self.user} - {self.file}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
