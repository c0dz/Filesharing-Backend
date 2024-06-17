import secrets
from django.utils import timezone
from rest_framework import serializers
from django.core.validators import EmailValidator
from accounts.models import UserModel, VerificationModel
from django.core.mail import send_mail
from .repository import UserRepository, VerificationRepository


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = UserModel
        fields = ["username", "email", "password", "confirm_password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_repository = UserRepository()

    def validate_username(self, value):
        # at least 4 letters
        if len(value) < 4:
            raise serializers.ValidationError(
                "Username must be at least 4 characters long."
            )
        # only english letters and no digits
        if not value.isalpha():
            raise serializers.ValidationError(
                "Username must contain only English letters."
            )

        # Commented out: it gets checked automatically
        # if self.user_repository.check_username_exists(value):
        #     raise serializers.ValidationError("Username already exists.")

        return value

    def validate_email(self, value):
        EmailValidator()(value)
        if self.user_repository.check_email_exists(value):
            raise serializers.ValidationError("Email already exists.")

        return value

    def validate_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError(
                "Password must be at least 6 characters long."
            )
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Password must contain a digit.")
        # lowercase check
        if not any(char.islower() for char in value):
            raise serializers.ValidationError(
                "Password must contain a lowercase letter."
            )
        # uppercase check
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError(
                "Password must contain an uppercase letter."
            )
        # symbol check
        if not any(
            char
            in [
                "@",
                "#",
                "$",
                "%",
                "&",
                "*",
                "+",
                "-",
                "/",
                ":",
            ]
            for char in value
        ):
            raise serializers.ValidationError(
                "Password must contain one of the symbols '@', '#', '$', '%', '&', '*', '+', '-', '/', ':'"
            )
        return value

    def validate_confirm_password(self, value):
        if self.initial_data["password"] != value:
            raise serializers.ValidationError("Passwords must match.")
        return value

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        user = self.user_repository.create_user(**validated_data)
        return user


class SendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_repository = UserRepository()
        self.verification_repository = VerificationRepository()

    def validate(self, attrs):
        email = attrs["email"]
        # wait for 1 second, then check if the user exists

        user = self.user_repository.filter(email=email)

        if not user.exists():
            raise serializers.ValidationError("User does not exist.")

        # if user[0].is_active:
        #     raise serializers.ValidationError("User is already verified.")

        return attrs

    def generate_token(self):
        return secrets.token_urlsafe(16)

    def create_verification_link(self):
        token = self.generate_token()
        expires_at = timezone.now() + timezone.timedelta(hours=1)
        email = self.validated_data["email"]
        user = UserModel.objects.get(email=email)

        link_verification = self.verification_repository.create(
            user=user, token=token, expires_at=expires_at
        )

        verification_url = (
            f"http://localhost:5173/verification/{user.id}/{link_verification.token}/"
        )

        return verification_url

    def send_verification_email(self):
        email = self.validated_data["email"]
        link = self.create_verification_link()

        subject = "Verification Email"
        message = f"Please click the following link to verify your account: {link}"
        from_email = "abcd@gmail.com"
        recipient_list = [email]
        send_mail(subject, message, from_email, recipient_list)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = ("id", "username", "photo")
