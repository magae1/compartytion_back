from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema

from .models import Account, Profile
from .serializers import (
    AccountCreationSerializer,
    EmailSerializer,
    EmailWithOTPSerializer,
    OTPRequestSerializer,
    AccountSerializer,
    PasswordChangeSerializer,
    ProfileSerializer,
    SimpleProfileSerializer,
    ProfileAvatarUploadSerializer,
)


class AuthViewSet(viewsets.GenericViewSet):
    serializer_class = AccountCreationSerializer
    queryset = Account.objects.all()
    permission_classes = [AllowAny]

    @extend_schema(request=EmailSerializer, responses={200: EmailSerializer})
    @action(methods=["POST"], detail=False, serializer_class=EmailSerializer)
    def check_email(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, serializer_class=TokenObtainPairSerializer)
    def login(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, serializer_class=EmailWithOTPSerializer)
    def verify_otp(self, request):
        serializer = EmailWithOTPSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, serializer_class=OTPRequestSerializer)
    def request_otp(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False)
    def signup(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AccountViewSet(viewsets.GenericViewSet):
    serializer_class = AccountSerializer
    queryset = Account.objects.all()
    permission_classes = [IsAuthenticated]

    @action(methods=["GET"], detail=False)
    def me(self, request):
        serializer = AccountSerializer(request.user, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["PATCH"],
        detail=False,
        serializer_class=PasswordChangeSerializer,
    )
    def change_password(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": _("비밀번호가 변경됐습니다.")}, status=status.HTTP_200_OK
        )

    @action(
        methods=["PATCH"],
        detail=False,
        serializer_class=ProfileSerializer,
    )
    def change_profile(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(instance=profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": _("변경사항이 적용됐습니다.")}, status=status.HTTP_200_OK
        )

    @action(
        methods=["PATCH"],
        detail=False,
        parser_classes=[MultiPartParser],
        serializer_class=ProfileAvatarUploadSerializer,
    )
    def upload_avatar(self, request):
        profile = request.user.profile
        serializer = ProfileAvatarUploadSerializer(
            instance=profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": _("프로필 아바타가 변경됐습니다.")}, status=status.HTTP_200_OK
        )

    @action(methods=["POST"], detail=False, serializer_class=OTPRequestSerializer)
    def request_otp(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["PATCH"], detail=False, serializer_class=EmailWithOTPSerializer)
    def change_email(self, request):
        serializer = EmailWithOTPSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": _("이메일이 변경됐습니다.")}, status=status.HTTP_200_OK
        )


class ProfileViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    serializer_class = SimpleProfileSerializer
    queryset = Profile.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = "username"

    @action(methods=["GET"], detail=False)
    def me(self, request):
        profile = get_object_or_404(self.get_queryset(), account=request.user)
        serializer = self.serializer_class(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
