from typing import Type
from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from accounts.models import UserModel, VerificationModel


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


class UserRepository(Repository):
    """Repository for User model."""

    def __init__(self):
        super().__init__(UserModel)

    def check_username_exists(self, username: str) -> bool:
        """Check if a user with the given username exists."""
        return self.filter(username=username).exists()

    def check_email_exists(self, email: str) -> bool:
        """Check if a user with the given email exists."""
        return self.filter(email=email).exists()

    def create_user(self, **kwargs) -> UserModel:
        """Create a new user instance with the given keyword arguments."""
        return UserModel.objects.create_user(**kwargs)

    def activate_user(self, user: UserModel) -> None:
        """Activate a user and save the changes."""
        user.is_active = True
        user.save()

    def get_all_active_users_except_current(
        self, current_user: UserModel
    ) -> models.QuerySet:
        """Get all active users except the current user."""
        return self.filter(is_active=True).exclude(id=current_user.id)


class VerificationRepository(Repository):
    """Repository for Verification model."""

    def __init__(self):
        super().__init__(VerificationModel)
