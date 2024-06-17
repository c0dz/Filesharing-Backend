from rest_framework import serializers
import datetime
from accounts.models import UserModel
from accounts.repository import UserRepository
from filesharing.models import FileModel
from .repository import FileRepository


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_repository = FileRepository()

    def validate_file(self, value):
        if value.size > 350 * 1024 * 1024:  # 350MB size limit
            raise serializers.ValidationError("File size should be less than 350MB")
        return value

    def file_path(self, file_id):
        # get user id from context
        user_id = self.context["user"].id
        # get file name
        original_filename = self.validated_data["file"].name
        # return file path
        return f"user_{user_id}/{file_id}_{original_filename}"

    def create(self, validated_data):
        owner = self.context["user"]
        new_file = self.file_repository.upload_file(validated_data, owner)
        return new_file


class ListFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileModel
        fields = "__all__"


class FileDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileModel
        fields = [
            "id",
            "original_filename",
            "file_extension",
            "size",
            "upload_date",
        ]

    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
        self.file_repository = FileRepository()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # 10:09pm, 10 Oct
        data["upload_date"] = instance.upload_date.strftime("%I:%M%p, %d %b")
        # size in B, KB, MB, or GB
        size = instance.size
        if size < 1024:
            data["size"] = size
            data["unit"] = "B"
        elif size < 1024**2:
            # with 2 decimal places
            data["size"] = (size / 1024).__format__(".0f")
            data["unit"] = "KB"
        elif size < 1024**3:
            data["size"] = (size / (1024**2)).__format__(".0f")
            data["unit"] = "MB"
        else:
            data["size"] = (size / (1024**3)).__format__(".0f")
            data["unit"] = "GB"

        # file permission
        data["permission"] = self.file_repository.get_file_permission_for_user(
            file=instance, user=self.context["user"]
        )

        return data


class ShareFileProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ("id", "email", "first_name", "last_name", "photo")

    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
        self.file_repository = FileRepository()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["is_shared"] = self.file_repository.check_permission(
            file=self.context["file"], user=instance
        )

        return data


class ShareFileSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    status = serializers.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_repository = UserRepository()
        self.file_repository = FileRepository()

    def validate_user_id(self, value):
        try:
            user = self.user_repository.get_or_raise(pk=value)
            # user = UserModel.objects.get(pk=value)
            owner = self.context["owner"]
            file = self.context["file"]

            if not user.is_active:
                raise serializers.ValidationError("User is not verified.")

            if user.id == owner.id:
                raise serializers.ValidationError(
                    "You cannot share the file with yourself :)"
                )

            if (
                self.file_repository.get_file_permission_for_user(file=file, user=owner)
                != "F"
            ):
                raise serializers.ValidationError(
                    "You do not have permission to share the file."
                )

        except UserModel.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return value

    def validate_status(self, value):
        if value not in ["denied", "access"]:
            raise serializers.ValidationError("Invalid status.")
        return value

    def create(self, validated_data):
        file = self.context["file"]
        user = UserModel.objects.get(pk=validated_data["user_id"])
        if validated_data["status"] == "access":
            self.file_repository.grant_read_permission(file=file, user=user)
            # FilePermissionModel.objects.create(file=file, user=user, permission="R")
        elif validated_data["status"] == "denied":
            self.file_repository.revoke_read_permission(file=file, user=user)
            # FilePermissionModel.objects.filter(file=file, user=user).delete()

        return file
