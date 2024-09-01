from datetime import timedelta
import random
from django.core import mail
from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from .models import Account, UnauthenticatedEmail


class AuthViewSetTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.account = Account.objects.create_user(
            email="user@example.com", password="password", username="test-user"
        )
        cls.unauthenticated_email = UnauthenticatedEmail.objects.create(
            email="un-auth@example.com"
        )
        cls.URL_PREFIX = "/api/auth"

    def test_check_email_with_empty_body(self):
        url = self.URL_PREFIX + "/check_email/"
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_email_with_invalid_email(self):
        url = self.URL_PREFIX + "/check_email/"
        res = self.client.post(url, {"email": "email123"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_check_email_with_already_signed_up_email(self):
        url = self.URL_PREFIX + "/check_email/"
        res = self.client.post(url, {"email": "user@example.com"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["exists"], True)

    def test_check_email_with_new_email(self):
        url = self.URL_PREFIX + "/check_email/"
        res = self.client.post(url, {"email": "user123@example.com"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["exists"], False)

    def test_check_email_with_unauthenticated_email(self):
        url = self.URL_PREFIX + "/check_email/"
        res = self.client.post(url, {"email": "un-auth@example.com"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["exists"], False)

    def test_request_otp_with_empty_body(self):
        url = self.URL_PREFIX + "/request_otp/"
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_otp_with_invalid_email(self):
        url = self.URL_PREFIX + "/request_otp/"
        res = self.client.post(url, {"email": "email123"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_otp_with_already_signed_up_email(self):
        url = self.URL_PREFIX + "/request_otp/"
        res = self.client.post(url, {"email": "user@example.com"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_otp_with_registered_email(self):
        url = self.URL_PREFIX + "/request_otp/"
        old_otp = self.unauthenticated_email.otp
        res = self.client.post(url, {"email": self.unauthenticated_email.email})
        new_otp = UnauthenticatedEmail.objects.get(
            email=self.unauthenticated_email.email
        ).otp
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], self.unauthenticated_email.email)
        self.assertNotEqual(mail.outbox[0].body, old_otp)
        self.assertEqual(mail.outbox[0].body, new_otp)
        self.assertGreater(
            timedelta(seconds=settings.OTP_SECONDS), res.data["remaining_time"]
        )
        mail.outbox.clear()

    def test_request_otp_with_new_email(self):
        url = self.URL_PREFIX + "/request_otp/"
        new_email = "new@example.com"
        res = self.client.post(url, {"email": new_email})
        new_otp = UnauthenticatedEmail.objects.get(email=new_email).otp
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], new_email)
        self.assertEqual(mail.outbox[0].body, new_otp)
        self.assertGreater(
            timedelta(seconds=settings.OTP_SECONDS), res.data["remaining_time"]
        )
        mail.outbox.clear()

    def test_verify_otp_with_empty_body(self):
        url = self.URL_PREFIX + "/verify_otp/"
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_otp_with_invalid_email(self):
        url = self.URL_PREFIX + "/verify_otp/"
        otp = self.unauthenticated_email.otp

        res = self.client.post(url, {"email": "123"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self.client.post(url, {"email": "123", "otp": otp})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_otp_with_invalid_otp(self):
        url = self.URL_PREFIX + "/verify_otp/"
        email = self.unauthenticated_email.email
        otp = self.unauthenticated_email.otp

        res = self.client.post(url, {"email": email})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UnauthenticatedEmail.objects.get(email=email).is_verified)

        res = self.client.post(url, {"email": email, "otp": otp[:5]})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UnauthenticatedEmail.objects.get(email=email).is_verified)

        res = self.client.post(url, {"email": email, "otp": otp + "-^*#FB"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UnauthenticatedEmail.objects.get(email=email).is_verified)

        random_otp = "".join(random.sample(otp, len(otp)))
        res = self.client.post(url, {"email": email, "otp": random_otp})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(UnauthenticatedEmail.objects.get(email=email).is_verified)

    def test_verify_otp_with_correct_otp(self):
        url = self.URL_PREFIX + "/verify_otp/"
        email = self.unauthenticated_email.email
        otp = self.unauthenticated_email.otp
        res = self.client.post(url, {"email": email, "otp": otp})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(UnauthenticatedEmail.objects.get(email=email).is_verified)


class AccountViewSetTestCase(APITestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            email="user1@example.com", password="password", username="test-user1"
        )
        self.token = AccessToken.for_user(self.account)
        self.URL_PREFIX = "/api/accounts"

    def test_me_with_unauthenticated_user(self):
        url = self.URL_PREFIX + "/me/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_with_authenticated_user(self):
        url = self.URL_PREFIX + "/me/"
        res = self.client.get(url, headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.account.id)
        self.assertEqual(res.data["email"], self.account.email)

    def test_change_password_with_unauthenticated_user(self):
        url = self.URL_PREFIX + "/change_password/"
        res = self.client.patch(
            url, {"password": "password", "new_password": "new-password"}
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_with_authenticated_user(self):
        url = self.URL_PREFIX + "/change_password/"
        res = self.client.patch(
            url,
            {"password": "password", "new_password": "new-password"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        account = Account.objects.get(id=self.account.id)
        self.assertTrue(account.check_password("new-password"))

    def test_request_otp_with_unauthenticated_user(self):
        url = self.URL_PREFIX + "/request_otp/"
        res = self.client.post(url, {"email": "new@example.com"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_request_otp_with_authenticated_user(self):
        url = self.URL_PREFIX + "/request_otp/"
        res = self.client.post(
            url,
            {"email": "new@example.com"},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            UnauthenticatedEmail.objects.filter(email="new@example.com").exists()
        )

    def test_change_email_with_unauthenticated_user(self):
        url = self.URL_PREFIX + "/change_email/"
        unauthenticated_email = UnauthenticatedEmail.objects.create(
            email="new@example.com", is_verified=True
        )
        res = self.client.patch(
            url,
            {"email": unauthenticated_email.email, "otp": unauthenticated_email.otp},
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_email_with_authenticated_user(self):
        url = self.URL_PREFIX + "/change_email/"
        unauthenticated_email = UnauthenticatedEmail.objects.create(
            email="new@example.com", is_verified=True
        )
        res = self.client.patch(
            url,
            {"email": unauthenticated_email.email, "otp": unauthenticated_email.otp},
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        account = Account.objects.get(id=self.account.id)
        self.assertEqual(account.email, "new@example.com")

    def test_change_profile_with_authenticated_user(self):
        Account.objects.create_user(
            email="user2@example.com", password="password", username="test-user2"
        )
        url = self.URL_PREFIX + "/change_profile/"
        authorization = f"Bearer {self.token}"
        res = self.client.patch(
            url,
            {"username": "test-user2"},
            headers={"Authorization": authorization},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.patch(
            url,
            {"username": "test-user123"},
            headers={"Authorization": authorization},
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class ProfileViewSetTestCase(APITestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            email="user@example.com", password="password", username="test-user"
        )
        self.token = AccessToken.for_user(self.account)
        self.URL_PREFIX = "/api/profiles"

    def test_me_with_unauthenticated_user(self):
        url = self.URL_PREFIX + "/me/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_with_authenticated_user(self):
        url = self.URL_PREFIX + "/me/"
        authorization = f"Bearer {self.token}"
        res = self.client.get(url, headers={"Authorization": authorization})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
