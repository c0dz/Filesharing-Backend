import math
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import boto3
from botocore.exceptions import ClientError
from rest_framework.permissions import IsAuthenticated
from accounts.models import UserModel
from accounts.repository import UserRepository
from filesharing.models import FileModel, FilePermissionModel
from filesharing.serializers import (
    FileDataSerializer,
    FileUploadSerializer,
    ShareFileProfileSerializer,
    ShareFileSerializer,
)
from django.core.paginator import Paginator
from core import settings
from rest_framework import generics
from django.db import transaction
from .utils import S3ResourceSingleton, S3ClientSingleton
from .repository import FileRepository


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

                s3_resource = S3ResourceSingleton()
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
        file_repository = FileRepository()
        return file_repository.get_all_files_for_user(user=self.request.user)

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
            user = request.user
            file_repository = FileRepository()
            file = file_repository.get_or_raise(pk=file_id)

            if not file_repository.check_user_is_owner(file, user):
                return Response(
                    {"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
                )
            file_permissions = file_repository.get_all_file_permissions(file)

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

        s3_resource = S3ResourceSingleton()

        try:
            file_repository.delete_file_from_s3(
                s3_resource=s3_resource,
                user=user,
                file=file,
                bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
            )

            file_repository.delete_file_from_db(file, file_permissions)

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


class DownloadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        try:
            file_repository = FileRepository()
            user = request.user
            file = file_repository.get_or_raise(pk=file_id)
            if not file_repository.check_permission(file, user):
                return Response(
                    {"message": "Permission denied"}, status=status.HTTP_403_FORBIDDEN
                )

            owner = file_repository.get_file_owner(file)

            s3_client = S3ClientSingleton()
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
            object_name = f"user_{owner.id}/{file.id}_{file.original_filename}"

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


class UserSharedListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        try:
            file_repository = FileRepository()
            user_repository = UserRepository()
            user = request.user
            file = file_repository.get_or_raise(pk=file_id)
            users = user_repository.get_all_active_users_except_current(user)
            serializer = ShareFileProfileSerializer(
                users, many=True, context={"file": file}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except FileModel.DoesNotExist:
            return Response(
                {"message": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except UserModel.DoesNotExist:
            return Response(
                {"message": "No users found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as exc:
            return Response(
                {"message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ShareFileView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, file_id):
        user = request.user
        received_data = request.data
        try:
            file_repository = FileRepository()
            file = file_repository.get_or_raise(pk=file_id)
            serializer = ShareFileSerializer(
                data=received_data, many=True, context={"file": file, "owner": user}
            )
            serializer.is_valid(raise_exception=True)

            serializer.save()
            return Response(
                {"message": "Sharing List Updated."}, status=status.HTTP_201_CREATED
            )
        except FileModel.DoesNotExist:
            return Response(
                {"message": "File not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as exc:
            return Response(
                {"message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
