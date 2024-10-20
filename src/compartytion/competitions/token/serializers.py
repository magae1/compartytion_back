from typing import Any, Dict, Optional, Type, TypeVar

from django.contrib.auth.hashers import check_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.serializers import PasswordField

from ..models import Participant
from .tokens import Token, PariticipantAccessToken


class TokenObtainSerializer(serializers.Serializer):
    id_field = "participant_id"
    token_class: Optional[Type[Token]] = None

    default_error_messages = {
        "no_active_account": _("No active account found with the given credentials")
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.fields[self.id_field] = serializers.CharField(write_only=True)
        self.fields["password"] = PasswordField()

    def validate(self, attrs: Dict[str, Any]) -> Dict[Any, Any]:
        try:
            self.participant = Participant.objects.get(id=attrs[self.id_field])
        except Participant.DoesNotExist:
            raise serializers.ValidationError(
                {self.id_field: _("존재하지 않는 참가자입니다.")}
            )

        if not check_password(attrs["password"], self.participant.password):
            raise serializers.ValidationError(
                {"password": _("비밀번호가 일치하지 않습니다.")}
            )

        return {}

    @classmethod
    def get_token(cls, participant: Participant) -> Token:
        return cls.token_class.for_participant(participant)  # type: ignore


class TokenObtainAccessSerializer(TokenObtainSerializer):
    token_class = PariticipantAccessToken

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        data = super().validate(attrs)

        access = self.get_token(self.participant)

        data["access"] = str(access)

        self.participant.update_last_login()

        return data
