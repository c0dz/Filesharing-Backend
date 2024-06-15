from decouple import config
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import boto3
from botocore.exceptions import ClientError
from rest_framework.permissions import IsAuthenticated
from filesharing.serializers import FileUploadSerializer

ARVAN_CLOUD = {
    "endpoint": config("ENDPOINT_URL"),
    "accesskey": config("ACCESS_KEY"),
    "secretkey": config("SECRET_KEY"),
    "bucket": config("BUCKET_NAME"),
}


class FileUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        file = request.FILES["file"]
        received_data = request.data
        print(received_data)
        serializer = FileUploadSerializer(
            data=received_data,
            context={
                "user": user,
            },
        )
        serializer.is_valid(raise_exception=True)
        file_details = serializer.save()

        file_path = serializer.file_path(
            cloud_name=file_details.cloud_name,
        )
        print(ARVAN_CLOUD["endpoint"])
        try:
            s3_resource = boto3.resource(
                "s3",
                endpoint_url=ARVAN_CLOUD["endpoint"],
                aws_access_key_id=ARVAN_CLOUD["accesskey"],
                aws_secret_access_key=ARVAN_CLOUD["secretkey"],
            )
        except Exception as exc:
            return Response(
                {"message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        else:
            try:
                bucket = s3_resource.Bucket(ARVAN_CLOUD["bucket"])
                bucket.put_object(ACL="private", Body=file, Key=file_path)

            except ClientError as e:
                return Response(
                    {"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response({"message": "File uploaded successfully"}, status=201)
