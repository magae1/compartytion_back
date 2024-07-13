from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from .models import Account, UnauthenticatedUser


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "email", "username", "password", "last_password_changed"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        new_account = Account.objects.create_user(**validated_data)
        return new_account


class AccountAuthSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["email", "password"]


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

    class Meta:
        fields = ["email"]

    def validate_email(self, email):
        if Account.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": _("이미 등록된 이메일입니다.")})
        return email


class EmailWithOTPSerializer(EmailSerializer):
    otp = serializers.CharField(
        required=True,
        validators=[
            RegexValidator(
                regex="^[0-9]{6}$", message="OTP는 반드시 6자로 입력되어야 합니다."
            )
        ],
    )

    class Meta:
        fields = ["email", "otp"]
        extra_kwargs = {"otp": {"write_only": True}}

    def validate(self, data):
        try:
            unauthenticated_user = UnauthenticatedUser.objects.get(email=data["email"])
            if unauthenticated_user.verify(data["otp"]):
                return data
            raise serializers.ValidationError({"otp": "OTP 인증에 실패했습니다."})
        except UnauthenticatedUser.DoesNotExist:
            raise serializers.ValidationError({"email": "찾을 수 없는 이메일입니다."})
