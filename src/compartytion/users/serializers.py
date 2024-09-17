from io import BytesIO
from django.conf import settings
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.files import File
from django.core.validators import MinLengthValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from rest_framework import serializers
from PIL import Image, ImageOps

from .models import Account, UnauthenticatedEmail, Profile


class AccountCreationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=30,
        validators=[MinLengthValidator(1), UnicodeUsernameValidator()],
        write_only=True,
    )

    class Meta:
        model = Account
        fields = ["id", "email", "username", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_username(self, username):
        if Profile.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(_("이미 존재하는 사용자명입니다."))
        return username

    def validate_email(self, email):
        if not UnauthenticatedEmail.objects.filter(
            email=email, is_verified=True
        ).exists():
            raise serializers.ValidationError(_("OTP 인증을 받지 않은 이메일입니다."))
        return email

    def create(self, validated_data):
        new_account = Account.objects.create_user(**validated_data)
        UnauthenticatedEmail.objects.get(
            email=new_account.email, is_verified=True
        ).delete()
        return new_account


class AccountAuthSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["email", "password"]


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    exists = serializers.BooleanField(read_only=True)

    class Meta:
        fields = ["email"]

    def to_representation(self, instance):
        exists = Account.objects.filter(email=self.validated_data["email"]).exists()
        return {"email": instance["email"], "exists": exists}


class EmailWithOTPSerializer(serializers.ModelSerializer):
    account = serializers.HiddenField(default=serializers.CurrentUserDefault())
    email = serializers.EmailField(required=True)

    class Meta:
        model = UnauthenticatedEmail
        fields = ["email", "otp", "is_verified", "account"]
        read_only_fields = ["is_verified"]
        extra_kwargs = {"otp": {"write_only": True, "required": True}}

    def validate(self, data):
        try:
            unauthenticated_email = UnauthenticatedEmail.objects.get(
                email=data["email"]
            )
            if unauthenticated_email.verify_otp(data["otp"], timezone.now()):
                unauthenticated_email.is_verified = True
                unauthenticated_email.save()
                return data
            raise serializers.ValidationError({"otp": "OTP 인증에 실패했습니다."})
        except UnauthenticatedEmail.DoesNotExist:
            raise serializers.ValidationError({"email": "찾을 수 없는 이메일입니다."})

    def save(self, **kwargs):
        UnauthenticatedEmail.objects.get(
            email=self.validated_data["email"], is_verified=True
        ).delete()
        account = self.validated_data["account"]
        account.email = self.validated_data["email"]
        account.clean()
        account.save()


class OTPRequestSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    remaining_time = serializers.DurationField(read_only=True)

    class Meta:
        model = UnauthenticatedEmail
        fields = ["email", "remaining_time"]

    def validate_email(self, email):
        if Account.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("이미 사용 중인 이메일입니다."))
        return email

    def to_representation(self, instance):
        time = UnauthenticatedEmail.objects.get(
            email=instance["email"]
        ).otp_time_remaining()
        return {
            "email": instance["email"],
            "remaining_time": time,
        }

    def save(self, **kwargs):
        instance = UnauthenticatedEmail(email=self.validated_data["email"])
        instance.email_user_with_otp()
        instance.save()


class PasswordChangeSerializer(serializers.Serializer):
    account = serializers.HiddenField(default=serializers.CurrentUserDefault())
    password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    class Meta:
        fields = ["owner", "password", "new_password"]
        extra_kwargs = {
            "password": {"write_only": True},
            "new_password": {"write_only": True},
        }

    def validate(self, data):
        if not data["account"].check_password(data["password"]):
            raise serializers.ValidationError(
                {"password": _("비밀번호가 일치하지 않습니다.")}
            )
        return data

    def save(self):
        self.validated_data["account"].update_password(
            self.validated_data["new_password"]
        )


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["username", "avatar", "introduction", "displayed_name", "hidden_name"]
        extra_kwargs = {"username": {"required": False}}

    def update(self, instance, validated_data):
        avatar = validated_data.pop("avatar", None)
        if avatar:
            with Image.open(avatar) as img:
                new_img = ImageOps.fit(img, settings.PROFILE_AVATAR_SIZE)

                if avatar.name.lower().endswith(".jpg") or avatar.name.lower().endswith(
                    ".jpeg"
                ):
                    format = "JPEG"
                elif avatar.name.lower().endswith(".png"):
                    format = "PNG"

                output = BytesIO()
                new_img.save(output, format=format, optimize=True)
                instance.avatar = File(output, name=avatar.name)
        return super().update(instance, validated_data)


class AccountSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(many=False, read_only=True)

    class Meta:
        model = Account
        fields = ["id", "email", "last_password_changed", "profile"]
        read_only_fields = ["email", "last_password_changed"]


class SimpleProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["username", "avatar"]
