from django.db import IntegrityError
from django.forms import ValidationError
from django.test import TestCase
from django.urls import reverse
from accounts.models import UserModel
from django.contrib.auth import authenticate


class UserModelTest(TestCase):
    def setUp(self):
        self.user = UserModel.objects.create(
            username="testuser",
            email="testuser@example.com",
            photo="user_photos/testuser.png",
            is_active=True,
        )

    def test_user_creation(self):
        self.assertIsInstance(self.user, UserModel)
        self.assertEqual(self.user.username, "testuser")
        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertTrue(self.user.is_active)

    def test_user_string_representation(self):
        self.assertEqual(str(self.user), "testuser")

    def test_email_uniqueness(self):
        with self.assertRaises(IntegrityError):
            UserModel.objects.create(
                username="anotheruser", email="testuser@example.com"
            )

    def test_username_uniqueness(self):
        with self.assertRaises(IntegrityError):
            UserModel.objects.create(
                username="testuser", email="anotheremail@example.com"
            )

    def test_invalid_email(self):
        user_with_invalid_email = UserModel(
            username="invalidemailuser", email="invalidemail"
        )
        with self.assertRaises(ValidationError):
            user_with_invalid_email.full_clean()

    def test_user_photo_path(self):
        self.assertEqual(self.user.photo, "user_photos/testuser.png")


class UserModelTest2(TestCase):
    def setUp(self):
        self.active_user = UserModel.objects.create_user(
            username="activeuser",
            email="activeuser@example.com",
            password="password123",
            is_active=True,
        )
        self.inactive_user = UserModel.objects.create_user(
            username="inactiveuser",
            email="inactiveuser@example.com",
            password="password123",
            is_active=False,
        )

    def test_login_inactive_user(self):
        # Attempt to authenticate inactive user
        user = authenticate(username="inactiveuser", password="password123")
        self.assertIsNone(user, "Inactive user should not be able to log in")

        # Attempt to log in inactive user via client
        response = self.client.post(
            reverse("login"), {"username": "inactiveuser", "password": "password123"}
        )
        self.assertEqual(response.status_code, 401)

    def test_login_active_user(self):
        # Attempt to authenticate active user
        user = authenticate(username="activeuser", password="password123")
        self.assertEqual(user, self.active_user, "Active user should be able to log in")

        # Attempt to log in active user via client
        response = self.client.post(
            reverse("login"), {"username": "activeuser", "password": "password123"}
        )
        self.assertEqual(response.status_code, 200)


class UserAuthenticationTest(TestCase):
    def setUp(self):
        self.registration_url = reverse("register")
        self.login_url = reverse("login")
        self.user = UserModel.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="password123",
            is_active=True,
        )

    ### Registration Tests ###

    def test_successful_registration(self):
        response = self.client.post(
            self.registration_url,
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "@NewP123",
                "confirm_password": "@NewP123",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(UserModel.objects.filter(username="newuser").exists())
        self.assertTrue(UserModel.objects.filter(email="newuser@example.com").exists())

    def test_registration_missing_fields(self):
        response = self.client.post(
            self.registration_url,
            {
                "username": "newuser",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        self.assertContains(response, "email", status_code=400)
        self.assertContains(response, "This field is required.", status_code=400)

    def test_registration_existing_email(self):
        response = self.client.post(
            self.registration_url,
            {
                "username": "anotheruser",
                "email": "testuser@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        self.assertContains(response, "email", status_code=400)
        self.assertContains(
            response, "User with this email already exists.", status_code=400
        )

    def test_registration_invalid_email(self):
        response = self.client.post(
            self.registration_url,
            {
                "username": "invalidemailuser",
                "email": "invalidemail",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        self.assertContains(response, "email", status_code=400)
        self.assertContains(response, "Enter a valid email address.", status_code=400)

    def test_registration_password_length(self):
        response = self.client.post(
            self.registration_url,
            {
                "username": "simplepassworduser",
                "email": "simplepassworduser@example.com",
                "password": "123",
                "confirm_password": "123",
            },
        )
        self.assertContains(
            response, "Password must be at least 6 characters long.", status_code=400
        )

    ### Login Tests ###

    def test_successful_login(self):
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "password123"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "access")
        self.assertContains(response, "refresh")

    def test_login_incorrect_password(self):
        response = self.client.post(
            self.login_url, {"username": "testuser", "password": "wrongpassword"}
        )

        self.assertContains(
            response,
            "No active account found with the given credentials",
            status_code=401,
        )

    def test_login_nonexistent_username(self):
        response = self.client.post(
            self.login_url, {"username": "nonexistentuser", "password": "password123"}
        )
        self.assertContains(
            response,
            "No active account found with the given credentials",
            status_code=401,
        )

    def test_login_inactive_user(self):
        inactive_user = UserModel.objects.create_user(
            username="inactiveuser",
            email="inactiveuser@example.com",
            password="password123",
            is_active=False,
        )
        response = self.client.post(
            self.login_url, {"username": "inactiveuser", "password": "password123"}
        )
        self.assertContains(
            response,
            "No active account found with the given credentials",
            status_code=401,
        )

    def test_login_case_insensitive_username(self):
        response = self.client.post(
            self.login_url, {"username": "TestUser", "password": "password123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "access")
        self.assertContains(response, "refresh")

    def test_login_case_insensitive_email(self):
        response = self.client.post(
            self.login_url,
            {"username": "testuser@example.com", "password": "password123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "access")
        self.assertContains(response, "refresh")
