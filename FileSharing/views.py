import math
from decouple import config
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import boto3
from botocore.exceptions import ClientError
from rest_framework.permissions import IsAuthenticated
from filesharing.models import FileModel, FilePermissionModel
from filesharing.serializers import (
    FileDataSerializer,
    FileUploadSerializer,
)
from django.core.paginator import Paginator
from core import settings
from rest_framework import generics
from django.db import transaction


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user

        file = request.FILES["file"]
        received_data = request.data
        serializer = FileUploadSerializer(
            data=received_data,
            context={
                "user": user,
            },
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            try:
                # begin
                file_details = serializer.save()

                file_path = serializer.file_path(
                    file_id=file_details,
                )

                s3_resource = boto3.resource(
                    "s3",
                    endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
            except Exception as exc:
                transaction.set_rollback(True)
                return Response(
                    {"message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            else:
                try:
                    bucket = s3_resource.Bucket(settings.AWS_STORAGE_BUCKET_NAME)
                    bucket.put_object(ACL="private", Body=file, Key=file_path)

                except ClientError as e:
                    transaction.set_rollback(True)
                    return Response(
                        {"message": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            return Response({"message": "File uploaded successfully"}, status=201)


class FileDataListView(generics.ListAPIView):
    serializer_class = FileDataSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # get file's related to the user from FilePermissionModel
        files = FilePermissionModel.objects.filter(user=self.request.user)
        # get the files details from FileModel
        file_ids = files.values_list("file_id", flat=True)
        # print file_ids to see the output
        for file_id in file_ids:
            print(file_id)
        files_data = FileModel.objects.filter(id__in=file_ids).order_by("-upload_date")
        return files_data

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        total_size_B = sum(file.size for file in queryset)
        total_size, unit = self.convert_size(total_size_B)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            total_pages = self.paginator.page.paginator.num_pages
            response_data = {
                "count": self.paginator.page.paginator.count,
                "next": self.paginator.get_next_link(),
                "previous": self.paginator.get_previous_link(),
                "total_pages": total_pages,
                "total_size": total_size,
                "unit": unit,
                "files": serializer.data,
            }
            return Response(response_data)

        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            "count": len(queryset),
            "next": None,
            "previous": None,
            "total_pages": "1",
            "total_size": total_size,
            "unit": unit,
            "files": serializer.data,
        }
        return Response(response_data)

    def convert_size(self, size_bytes):
        if size_bytes == 0:
            return (0, "B")
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = size_bytes / p
        return (round(s, 3), size_name[i])
