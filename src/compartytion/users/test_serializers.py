import sys
from io import BytesIO
from django.test import TestCase
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

from .serializers import ProfileSerializer, AccountCreationSerializer
from .models import Profile, Account, UnauthenticatedEmail


class ProfileSerializerTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        account = Account.objects.create_user(
            email="user@example.com", password="password", username="user"
        )
        cls.profile = Profile.objects.get(account_id=account.id)

    def test_update_profile_avatar(self):
        image = Image.new("RGB", (123, 456))
        output = BytesIO()
        image.save(output, format="JPEG")
        output.seek(0)
        sample_img = InMemoryUploadedFile(
            output, "ImageField", "test.jpg", "image/jpeg", sys.getsizeof(output), None
        )
        serializer = ProfileSerializer(
            instance=self.profile, data={"avatar": sample_img}, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        profile = Profile.objects.get(account_id=self.profile.account_id)
        (profile_width, profile_height) = (profile.avatar.width, profile.avatar.height)
        self.assertEqual((profile_width, profile_height), settings.PROFILE_AVATAR_SIZE)

    def test_update_profile_username(self):
        serializer = ProfileSerializer(
            instance=self.profile, data={"username": "me"}, partial=True
        )
        self.assertFalse(serializer.is_valid(raise_exception=False))
        self.assertEqual(
            serializer.errors["username"][0], "사용할 수 없는 사용자명입니다."
        )


class AccountCreationSerializerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        UnauthenticatedEmail.objects.create(email="user@example.com", is_verified=True)

    def test_account_creation(self):
        new_account_data = {
            "email": "user@example.com",
            "password": "password",
            "username": "me",
        }
        serializer = AccountCreationSerializer(data=new_account_data)
        self.assertFalse(serializer.is_valid(raise_exception=False))
        self.assertEqual(
            serializer.errors["username"][0], "사용할 수 없는 사용자명입니다."
        )
