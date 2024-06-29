from django.test import TestCase
from accounts.models import UserModel
from accounts.serializers import (
    RegisterSerializer,
    SendVerificationEmailSerializer,
    ProfileSerializer,
)
from unittest.mock import patch
from django.core.exceptions import ValidationError


class RegisterSerializerTest(TestCase):

    def setUp(self):
        self.user_data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "@@TEqqq123!",
            "confirm_password": "@@TEqqq123!",
        }

    def test_valid_data(self):
        serializer = RegisterSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_username_too_short(self):
        self.user_data["username"] = "usr"
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)

    def test_invalid_username_non_alpha(self):
        self.user_data["username"] = "user123"
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)

    def test_invalid_email(self):
        self.user_data["email"] = "invalidemail"
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_password_too_short(self):
        self.user_data["password"] = "Pwd1!"
        self.user_data["confirm_password"] = "Pwd1!"
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_password_no_digit(self):
        self.user_data["password"] = "Password!"
        self.user_data["confirm_password"] = "Password!"
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)
        self.assertIn("Password must contain a digit.", str(serializer.errors))

    def test_password_no_lowercase(self):
        self.user_data["password"] = "PASSWORD1!"
        self.user_data["confirm_password"] = "PASSWORD1!"
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_password_no_uppercase(self):
        self.user_data["password"] = "password1!"
        self.user_data["confirm_password"] = "password1!"
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_password_no_symbol(self):
        self.user_data["password"] = "Password1"
        self.user_data["confirm_password"] = "Password1"
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_passwords_do_not_match(self):
        self.user_data["confirm_password"] = "Different123!"
        serializer = RegisterSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("confirm_password", serializer.errors)

    def test_create_user(self):
        serializer = RegisterSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertIsInstance(user, UserModel)
        self.assertEqual(user.username, self.user_data["username"])


class SendVerificationEmailSerializerTest(TestCase):

    def setUp(self):
        self.user_data = {
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "Password123!",
        }
        self.user = UserModel.objects.create_user(**self.user_data)
        self.serializer_data = {"email": self.user.email}

    def test_valid_email(self):
        serializer = SendVerificationEmailSerializer(data=self.serializer_data)
        self.assertTrue(serializer.is_valid())

    def test_invalid_email(self):
        invalid_data = {"email": "invalidemail"}
        serializer = SendVerificationEmailSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_user_does_not_exist(self):
        non_existent_email = {"email": "nonexistent@example.com"}
        serializer = SendVerificationEmailSerializer(data=non_existent_email)
        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_generate_token(self):
        serializer = SendVerificationEmailSerializer(data=self.serializer_data)
        token = serializer.generate_token()
        self.assertEqual(len(token), 22)  # length of a token_urlsafe(16)

    def test_create_verification_link(self):
        serializer = SendVerificationEmailSerializer(data=self.serializer_data)
        serializer.is_valid()
        link = serializer.create_verification_link()
        self.assertIn("http://localhost:5173/verification", link)

    @patch("accounts.serializers.send_mail")
    def test_send_verification_email(self, mock_send_mail):
        serializer = SendVerificationEmailSerializer(data=self.serializer_data)
        serializer.is_valid()
        serializer.send_verification_email()
        self.assertTrue(mock_send_mail.called)


class ProfileSerializerTest(TestCase):

    def setUp(self):
        self.user = UserModel.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="Password123!",
            photo="path/to/photo.jpg",
        )
        self.serializer = ProfileSerializer(instance=self.user)

    def test_profile_serializer_fields(self):
        data = self.serializer.data
        self.assertEqual(set(data.keys()), set(["id", "username", "photo"]))
        self.assertEqual(data["username"], self.user.username)
