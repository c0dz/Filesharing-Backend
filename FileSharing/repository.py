from typing import Type
from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from .models import FileModel, FilePermissionModel


class ObjectNotFoundException(Exception):
    """Raised when an object is not found."""

    def __init__(self, message):
        self.message = message


class Repository:
    """Base repository class providing common CRUD operations."""

    def __init__(self, model: Type[models.Model]):
        self.model = model

    def get_or_raise(self, **kwargs) -> models.Model:
        """Retrieve an instance by keyword arguments. Raise ObjectNotFoundException if not found."""
        try:
            return self.model.objects.get(**kwargs)
        except ObjectDoesNotExist:
            raise ObjectNotFoundException(
                f"{self.model.__name__} not found for {kwargs}"
            )

    def create(self, **kwargs) -> models.Model:
        """Create a new instance with the given keyword arguments."""
        return self.model.objects.create(**kwargs)

    def delete(self, instance: models.Model) -> None:
        """Delete an instance."""
        instance.delete()

    def filter(self, **kwargs) -> models.QuerySet:
        """Filter instances by keyword arguments."""
        return self.model.objects.filter(**kwargs)


class FileRepository(Repository):
    """Repository for File model."""

    def __init__(self):
        super().__init__(FileModel)

    def upload_file(self, validated_data, owner) -> FileModel:
        """Upload a file."""
        file = validated_data.pop("file")
        file_extension = file.name.split(".")[-1]
        file_instance = FileModel.objects.create(
            original_filename=file.name,
            size=file.size,
            file_extension=file_extension,
            **validated_data,
        )
        FilePermissionModel.objects.create(
            file=file_instance, user=owner, permission="F"
        )
        return file_instance

    def get_all_files_for_user(self, user) -> models.QuerySet:
        """Get all files for a user."""
        file_ids = FilePermissionModel.objects.filter(user=user).values_list(
            "file_id", flat=True
        )
        return FileModel.objects.filter(id__in=file_ids).order_by("-upload_date")

    def get_file_permission_for_user(self, file, user) -> str:
        """Get file permission for a user."""
        permission_instance = FilePermissionModel.objects.get(file=file, user=user)
        return permission_instance.permission

    def check_permission(self, file, user) -> bool:
        """Check if a user has permission to access a file."""
        try:
            FilePermissionModel.objects.get(file=file, user=user)
            return True
        except ObjectDoesNotExist:
            return False

    def grant_read_permission(self, file, user) -> FilePermissionModel:
        """Grant a specific permission to a user for a file."""
        return FilePermissionModel.objects.create(file=file, user=user, permission="R")

    def revoke_read_permission(self, file, user) -> None:
        """Revoke read permission of a user for a file."""
        FilePermissionModel.objects.filter(
            file=file, user=user, permission="R"
        ).delete()

    def delete_file_from_db(self, file, file_permissions) -> None:
        """Delete a file and its permissions from the database."""
        file_permissions.delete()
        file.delete()

    def delete_file_from_s3(self, s3_resource, bucket_name, file, user) -> None:
        """Delete a file from S3."""
        object_name = f"user_{user.id}/{file.id}_{file.original_filename}"
        bucket = s3_resource.Bucket(bucket_name)
        s3_object = bucket.Object(object_name)
        s3_object.delete()

    def check_user_is_owner(self, file, user) -> bool:
        """Check if a user is the owner of a file."""
        return FilePermissionModel.objects.filter(
            file=file, user=user, permission="F"
        ).exists()

    def get_all_file_permissions(self, file) -> models.QuerySet:
        """Get all permissions for a file."""
        return FilePermissionModel.objects.filter(file=file)

    def get_file_owner(self, file) -> models.Model:
        """Get the owner of a file."""
        return FilePermissionModel.objects.get(file=file, permission="F").user


class FilePermissionRepository(Repository):
    """Repository for FilePermission model."""

    def __init__(self):
        super().__init__(FilePermissionModel)

    def has_permission(self, user, file, permission_type) -> bool:
        """Check if a user has a specific permission on a file."""
        return self.filter(user=user, file=file, permission=permission_type).exists()

    def grant_permission(self, user, file, permission_type) -> FilePermissionModel:
        """Grant a specific permission to a user for a file."""
        return self.create(user=user, file=file, permission=permission_type)

    def revoke_permission(self, user, file) -> None:
        """Revoke all permissions of a user for a file."""
        permissions = self.filter(user=user, file=file)
        for permission in permissions:
            self.delete(permission)
