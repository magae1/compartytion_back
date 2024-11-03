from typing import Any, Dict, Optional, Type

from django.contrib.auth.hashers import check_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import PasswordField

from ..models import Participant
from .tokens import Token, ParticipantAccessToken


class TokenObtainSerializer(serializers.Serializer):
    id_field = "access_id"
    password_field = "access_password"
    token_class: Optional[Type[Token]] = None

    default_error_messages = {
        "no_active_account": _("No active account found with the given credentials")
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.participant = None
        self.fields[self.id_field] = serializers.CharField(write_only=True)
        self.fields[self.password_field] = PasswordField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        try:
            self.participant = Participant.objects.get(access_id=attrs[self.id_field])
        except Participant.DoesNotExist:
            raise serializers.ValidationError(
                {self.id_field: _("존재하지 않는 참가자입니다.")}
            )

        if not check_password(attrs[self.password_field], self.participant.password):
            raise serializers.ValidationError(
                {self.password_field: _("비밀번호가 일치하지 않습니다.")}
            )

        return {}

    @classmethod
    def get_token(cls, participant: Participant) -> Token:
        return cls.token_class.for_participant(participant)  # type: ignore


class TokenObtainAccessSerializer(TokenObtainSerializer):
    token_class = ParticipantAccessToken

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        data = super().validate(attrs)

        access = self.get_token(self.participant)

        data["access"] = str(access)

        self.participant.update_last_login()

        return data
