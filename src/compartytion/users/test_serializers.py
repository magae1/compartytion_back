import sys
from io import BytesIO
from django.test import TestCase
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

from .serializers import ProfileSerializer
from .models import Profile, Account


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
