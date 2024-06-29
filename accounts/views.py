from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.models import UserModel, VerificationModel
from accounts.serializers import (
    ProfileSerializer,
    RegisterSerializer,
    SendVerificationEmailSerializer,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from .repository import UserRepository, VerificationRepository


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
        try:
            user_repository = UserRepository()
            verification_repository = VerificationRepository()
            user = user_repository.get_or_raise(pk=user_id)
        except UserModel.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            # check if the token is valid
            try:
                link_verification = verification_repository.get_or_raise(
                    user=user, token=token
                )
            except VerificationModel.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            else:
                # check if the token has expired
                if link_verification.expires_at < timezone.now():
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                else:
                    user_repository.activate_user(user)
                    link_verification.delete()
                    return Response(status=status.HTTP_200_OK)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = ProfileSerializer(instance=user)

        return Response(serializer.data, status=status.HTTP_200_OK)


class ValidateAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_active:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
