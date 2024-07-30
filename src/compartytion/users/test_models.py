from datetime import timedelta
from django.test import TestCase
from django.core import mail
from django.conf import settings
from django.utils import timezone

from .models import Account, Profile, UnauthenticatedEmail


class AccountTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Account.objects.create_user(
            email="hello@example.com", username="test_user", password="password123"
        )

    def test_password_update(self):
        account = Account.objects.get(email="hello@example.com")
        last_password_changed = account.last_password_changed
        account.update_password("new_password123")

        self.assertTrue(account.check_password("new_password123"))
        self.assertNotEqual(last_password_changed, account.last_password_changed)

    def test_email(self):
        account = Account.objects.get(email="hello@example.com")
        subject = "hi!"
        message = f"welcome! {account.username}"
        account.email_user(subject, message, fail_silently=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, subject)
        self.assertEqual(mail.outbox[0].body, message)


class UnauthenticatedEmailTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        UnauthenticatedEmail.objects.create(email="hello@example.com")

    def test_otp_validation(self):
        unauthenticated_email = UnauthenticatedEmail.objects.get(
            email="hello@example.com"
        )
        cases = [
            ("_#^*&%", timezone.now()),
            ("가나다", timezone.now()),
            ("123", timezone.now()),
            ("abcdef", timezone.now()),
            (unauthenticated_email.otp, timezone.now() + timedelta(minutes=6)),
        ]
        for case in cases:
            self.assertFalse(unauthenticated_email.verify_otp(case[0], case[1]))
        self.assertTrue(
            unauthenticated_email.verify_otp(unauthenticated_email.otp, timezone.now())
        )

    def test_send_otp(self):
        unauthenticated_email = UnauthenticatedEmail.objects.get(
            email="hello@example.com"
        )
        unauthenticated_email.email_user_with_otp(fail_silently=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "OTP 인증코드")
        self.assertEqual(mail.outbox[0].to[0], unauthenticated_email.email)
        self.assertEqual(mail.outbox[0].body, unauthenticated_email.otp)

    def test_otp_remaining_time(self):
        unauthenticated_email = UnauthenticatedEmail.objects.get(
            email="hello@example.com"
        )
        remaining = unauthenticated_email.otp_time_remaining()
        self.assertGreater(timedelta(seconds=settings.OTP_SECONDS), remaining)


class ProfileTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Account.objects.create_user(
            email="hello@example.com", username="test_user", password="password123"
        )

    def test_profile_auto_creation(self):
        filtered_accounts = Account.objects.filter(email="hello@example.com")
        self.assertTrue(filtered_accounts.exists())
        account = filtered_accounts.first()
        filtered_profiles = Profile.objects.filter(account_id__exact=account.id)
        self.assertTrue(filtered_profiles.exists())
        profile = filtered_profiles.first()
        self.assertEqual(profile.account.id, account.id)

    def test_profile_auto_deletion(self):
        account = Account.objects.create_user(
            email="user@example.com", username="test_user1", password="password123"
        )
        account_id = account.id
        account.delete()
        with self.assertRaises(Profile.DoesNotExist):
            Profile.objects.get(account=account_id)
