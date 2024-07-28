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
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    AccountCreationSerializer,
    EmailSerializer,
    EmailWithOTPSerializer,
    OTPRequestSerializer,
    AccountSerializer,
    PasswordChangeSerializer,
    ProfileSerializer,
    UsernameChangeSerializer,
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
        serializer = EmailWithOTPSerializer(data=request.data)
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
        return Response(serializer.data, status=status.HTTP_200_OK)


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
            {"detail": "비밀번호가 변경됐습니다."}, status=status.HTTP_200_OK
        )

    @action(methods=["PATCH"], detail=False, serializer_class=UsernameChangeSerializer)
    def change_username(self, request):
        serializer = UsernameChangeSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": _("사용자명이 변경됐습니다.")}, status=status.HTTP_200_OK
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
    serializer_class = ProfileSerializer
    queryset = Profile.objects.all()
    parser_classes = [MultiPartParser]
    permission_classes = [IsOwnerOrReadOnly]

    @action(methods=["GET", "PATCH"], detail=False)
    def me(self, request):
        if request.user is None or request.user.is_anonymous:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        profile = get_object_or_404(self.get_queryset(), account=request.user)
        if request.method == "GET":
            serializer = self.get_serializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(
            instance=profile, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            data={"detail": _("프로필이 변경됐습니다.")}, status=status.HTTP_200_OK
        )
