from rest_framework import serializers
import datetime
from filesharing.models import FileModel, FilePermissionModel


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if value.size > 350 * 1024 * 1024:  # 350MB size limit
            raise serializers.ValidationError("File size should be less than 350MB")
        return value

    def file_path(self, cloud_name):
        # get user id from context
        user_id = self.context["user"].id
        # get file name
        cloud_name = cloud_name
        original_filename = self.validated_data["file"].name
        # return file path
        return f"user_{user_id}/{cloud_name}_{original_filename}"

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
            file=file_instance, user=self.context["user"], permission="full"
        )
        return file_instance
