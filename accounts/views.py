from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.models import UserModel, VerificationModel
from accounts.serializers import RegisterSerializer, SendVerificationEmailSerializer
from rest_framework.permissions import AllowAny
from django.utils import timezone


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyLinkView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendVerificationEmailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.send_verification_email()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, user_id, token):
        # check if the user exists
        try:
            print(user_id, token)
            user = UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            # check if the token is valid
            try:
                link_verification = VerificationModel.objects.get(
                    user=user, token=token
                )
            except VerificationModel.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            else:
                # check if the token has expired
                if link_verification.expires_at < timezone.now():
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                else:
                    user.is_active = True
                    user.save()
                    link_verification.delete()
                    return Response(status=status.HTTP_200_OK)
