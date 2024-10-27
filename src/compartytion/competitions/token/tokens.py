from typing import TypeVar, Type
from django.conf import settings
from rest_framework_simplejwt.tokens import Token

from ..models import Participant

JWT_SETTINGS = getattr(settings, "SIMPLE_JWT", {})

T = TypeVar("T", bound="Token")


class ParticipantToken(Token):

    @classmethod
    def for_participant(cls: Type[T], participant: Participant) -> T:
        participant_id = getattr(participant, JWT_SETTINGS.get("PARTICIPANT_ID_FIELD"))

        participant_id = str(participant_id)

        token = cls()
        token[JWT_SETTINGS.get("PARTICIPANT_ID_CLAIM")] = participant_id

        return token


class ParticipantAccessToken(Participant):
    token_type = "access"
    lifetime = JWT_SETTINGS.get("ACCESS_TOKEN_LIFETIME")
