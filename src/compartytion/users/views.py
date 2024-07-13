from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema

from .models import Account, UnauthenticatedUser
from .serializers import AccountSerializer, EmailSerializer, EmailWithOTPSerializer


class AuthViewSet(viewsets.GenericViewSet):
    serializer_class = AccountSerializer
    queryset = Account.objects.all()
    permission_classes = [AllowAny]

    @extend_schema(request=EmailSerializer, responses={200})
    @action(methods=["POST"], detail=False, serializer_class=EmailSerializer)
    def check_email(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unauthenticated_user = UnauthenticatedUser(
            email=serializer.validated_data["email"]
        )
        unauthenticated_user.email_user_with_otp()
        unauthenticated_user.save()
        return Response(status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, serializer_class=TokenObtainPairSerializer)
    def login(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, serializer_class=EmailWithOTPSerializer)
    def confirm_otp(self, request):
        serializer = EmailWithOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, serializer_class=EmailSerializer)
    def resend_otp(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unauthenticated_user = UnauthenticatedUser(
            email=serializer.validated_data["email"]
        )
        unauthenticated_user.email_user_with_otp()
        unauthenticated_user.save()
        return Response(status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False)
    def signup(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
