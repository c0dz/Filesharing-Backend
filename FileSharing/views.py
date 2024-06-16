import math
from decouple import config
from django.http import HttpResponse
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


def get_s3_resource():
    return boto3.resource(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


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
                    file_id=file_details.id,
                )

                s3_resource = get_s3_resource()
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


class DeleteFileView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, file_id):
        try:
            file = FileModel.objects.get(id=file_id)
            file_permission = FilePermissionModel.objects.get(
                file=file, user=request.user, permission="F"
            )
            print("PASS1")
        except FileModel.DoesNotExist:
            return Response(
                {"message": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except FilePermissionModel.DoesNotExist:
            return Response(
                {"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )
        except Exception as exc:
            return Response(
                {"message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        s3_resource = get_s3_resource()
        print("PASS2")

        try:
            self.delete_file_from_s3(s3_resource, request.user.id, file)
            print("PASS3")

            self.delete_file_records(file, file_permission)
            print("PASS4")

            return Response(
                {"message": "File deleted successfully"}, status=status.HTTP_200_OK
            )
        except ClientError as e:
            return Response(
                {"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as exc:
            return Response(
                {"message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete_file_from_s3(self, s3_resource, user_id, file):
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        object_name = f"user_{user_id}/{file.id}_{file.original_filename}"
        bucket = s3_resource.Bucket(bucket_name)
        s3_object = bucket.Object(object_name)
        s3_object.delete()

    def delete_file_records(self, file, file_permission):
        # delete all the permissions related to the file
        shared_permissions = FilePermissionModel.objects.filter(file=file)
        file_permission.delete()
        shared_permissions.delete()

        # delete the file
        file.delete()


class DownloadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        try:
            user = request.user
            file = FileModel.objects.get(id=file_id)
            file_permission = FilePermissionModel.objects.get(
                file=file, user=user, permission__in=["R", "F"]
            )

            s3_client = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        except FileModel.DoesNotExist:
            return Response(
                {"message": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except FilePermissionModel.DoesNotExist:
            return Response(
                {"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
            )
        except Exception as exc:
            return Response(
                {"message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            object_name = f"user_{user.id}/{file.id}_{file.original_filename}"

            response = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": object_name},
                ExpiresIn=60 * 5,  # 5 minutes to expire
            )

            return Response({"url": response}, status=status.HTTP_200_OK)

        except ClientError as e:
            return Response(
                {"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as exc:
            return Response(
                {"message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
