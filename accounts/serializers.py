import secrets
from django.utils import timezone
from rest_framework import serializers
from django.core.validators import EmailValidator
from accounts.models import UserModel, VerificationModel
from django.core.mail import send_mail
from rest_framework.validators import UniqueValidator


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = UserModel
        fields = ["username", "email", "password", "confirm_password"]

    def validate_username(self, value):
        # at least 4 characters
        if len(value) < 4:
            raise serializers.ValidationError(
                "Username must be at least 4 characters long."
            )
        # only english letters and no digits
        if not value.isalpha():
            raise serializers.ValidationError(
                "Username must contain only English letters."
            )
        if UserModel.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")

        return value

    def validate_email(self, value):
        EmailValidator()(value)
        if UserModel.objects.filter(email=value).exists():
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
        user = UserModel.objects.create_user(**validated_data)
        return user


class SendVerificationEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"]
        # wait for 1 second, then check if the user exists

        user = UserModel.objects.filter(email=email)

        # the user must exist, if not we try again, it takes time to register the user, so we wait

        # if not user.exists():
        #     raise serializers.ValidationError("User does not exist.")
        # # check if email is already verified
        # if user.first().is_active:
        #     print("Email is already verified.")
        #     raise serializers.ValidationError("Email is already verified.")

        print("Validated")
        return attrs

    def generate_token(self):
        return secrets.token_urlsafe(16)

    def create_verification_link(self):
        token = self.generate_token()
        expires_at = timezone.now() + timezone.timedelta(hours=1)
        email = self.validated_data["email"]
        print(email)
        user = UserModel.objects.get(email=email)

        link_verification = VerificationModel.objects.create(
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
