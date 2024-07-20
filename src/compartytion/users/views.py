from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema

from .models import Account
from .serializers import (
    AccountCreationSerializer,
    EmailSerializer,
    EmailWithOTPSerializer,
    OTPRequestSerializer,
    AccountSerializer,
    PasswordChangeSerializer,
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

    @action(methods=["GET", "PUT", "PATCH"], detail=False)
    def me(self, request):
        if request.method == "GET":
            serializer = AccountSerializer(request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["PUT", "PATCH"],
        detail=False,
        serializer_class=PasswordChangeSerializer,
    )
    def change_password(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)
