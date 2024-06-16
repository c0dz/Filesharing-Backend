from rest_framework import serializers
import datetime
from filesharing.models import FileModel, FilePermissionModel


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

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
        file = validated_data.pop("file")
        file_extension = file.name.split(".")[-1]
        file_instance = FileModel.objects.create(
            original_filename=file.name,
            size=file.size,
            file_extension=file_extension,
            **validated_data,
        )
        file_permission_instance = FilePermissionModel.objects.create(
            file=file_instance, user=self.context["user"], permission="F"
        )
        return file_instance


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
            data["size"] = (size / 1024).__format__(".2f")
            data["unit"] = "KB"
        elif size < 1024**3:
            data["size"] = (size / (1024**2)).__format__(".2f")
            data["unit"] = "MB"
        else:
            data["size"] = (size / (1024**3)).__format__(".2f")
            data["unit"] = "GB"

        # file permission
        permission = FilePermissionModel.objects.get(
            file=instance, user=self.context["user"]
        )
        data["permission"] = permission.permission

        return data
