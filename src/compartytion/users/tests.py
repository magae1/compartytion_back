from django.test import TestCase
from .models import Account, UnauthenticatedUser


class AccountTestCase(TestCase):
    def setUp(self):
        Account.objects.create_user(
            email="hello@EXAMPLE.COM", username="test_user", password="fake_123"
        )

    def test_password_update(self):
        account = Account.objects.get(email="hello@example.com")
        last_password_changed = account.last_password_changed
        account.update_password("new_password")
        self.assertNotEqual(last_password_changed, account.last_password_changed)
