from datetime import timedelta
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.conf import settings
from django.core.mail import send_mail
from django.core.validators import RegexValidator, MinLengthValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .utils import generate_otp, avatar_directory_path


class AccountManager(BaseUserManager):
    def create_user(self, email, username, password=None, **kwargs):
        if email is None:
            raise ValueError("이메일은 반드시 입력해야 합니다.")
        if username is None:
            raise ValueError("사용자명은 반드시 입력해야 합니다.")
        email = self.normalize_email(email)
        account = self.model(email=email, **kwargs)
        account.set_password(password)
        account.save(using=self._db)
        Profile.objects.create(account=account, username=username)
        return account

    def create_superuser(self, **kwargs):
        kwargs.setdefault("is_staff", True)
        kwargs.setdefault("is_superuser", True)

        if kwargs.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if kwargs.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(**kwargs)

    def get_by_natural_key(self, email):
        normalized_email = self.normalize_email(email)
        return self.get(**{self.model.USERNAME_FIELD: normalized_email})


class Account(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("이메일 주소", unique=True)
    is_staff = models.BooleanField("관리자 여부", default=False)
    is_active = models.BooleanField("활성 여부", default=True)
    date_joined = models.DateTimeField(
        "가입 일자", default=timezone.now, editable=False
    )
    last_password_changed = models.DateTimeField(
        "최근 비밀번호 변경일", default=timezone.now, editable=False
    )

    USERNAME_FIELD = "email"

    objects = AccountManager()

    class Meta:
        verbose_name = "계정"
        verbose_name_plural = "계정들"

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email

    def email_user(self, subject, message, from_email=None, **kwargs):
        send_mail(subject, message, from_email, [self.email], **kwargs)

    def update_password(self, password):
        self.set_password(password)
        self.last_password_changed = timezone.now()
        self.save()


class UnauthenticatedEmail(models.Model):
    email = models.EmailField(primary_key=True, unique=True)
    otp = models.TextField(
        default=generate_otp,
        null=False,
        blank=False,
        validators=[
            RegexValidator(
                regex="^[0-9]{6}$", message="OTP는 반드시 6자로 입력되어야 합니다."
            )
        ],
    )
    created_at = models.DateTimeField(
        default=timezone.now, null=False, blank=False, editable=False
    )
    is_verified = models.BooleanField(default=False, null=False, blank=False)

    objects = BaseUserManager()

    class Meta:
        verbose_name = "인증되지 않은 사용자"
        verbose_name_plural = "인증되지 않은 사용자들"

    def __str__(self):
        return f"{self.email}"

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email)
        super().save(*args, **kwargs)

    def email_user_with_otp(self, from_email=None, **kwargs):
        send_mail(_("OTP 인증코드"), self.otp, from_email, [self.email], **kwargs)

    def verify_otp(self, otp: str, current_time) -> bool:
        is_valid_time = current_time - self.created_at < timedelta(
            seconds=settings.OTP_SECONDS
        )
        if is_valid_time and otp == self.otp:
            return True
        return False

    def otp_time_remaining(self) -> timedelta:
        return (
            self.created_at + timedelta(seconds=settings.OTP_SECONDS) - timezone.now()
        )


class Profile(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, primary_key=True)
    username = models.CharField(
        "사용자명",
        max_length=30,
        unique=True,
        null=False,
        validators=[
            MinLengthValidator(1),
            UnicodeUsernameValidator(),
        ],
        error_messages={
            "unique": "이미 존재하는 사용자명입니다.",
        },
    )
    avatar = models.ImageField("아바타", upload_to=avatar_directory_path, null=True)
    displayed_name = models.CharField(
        "공개 이름", validators=[UnicodeUsernameValidator()], blank=True, max_length=30
    )
    hidden_name = models.CharField(
        "비공개 이름",
        validators=[UnicodeUsernameValidator()],
        blank=True,
        max_length=30,
    )
    introduction = models.TextField("소개", blank=True, max_length=255)

    class Meta:
        verbose_name = "프로필"
        verbose_name_plural = "프로필들"
