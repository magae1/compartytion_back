from typing import Optional, Tuple, Set

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import HTTP_HEADER_ENCODING, authentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .models import Participant
from .token.tokens import Token

JWT_SETTINGS = getattr(settings, "SIMPLE_JWT", {})

AUTH_HEADER_TYPES = JWT_SETTINGS.AUTH_HEADER_TYPES

AUTH_HEADER_TYPE_BYTES: Set[bytes] = {
    h.encode(HTTP_HEADER_ENCODING) for h in JWT_SETTINGS.AUTH_HEADER_TYPES
}


class JWTAuthentication(authentication.BaseAuthentication):
    www_authenticate_realm = "api"
    media_type = "application/json"

    def authenticate(self, request: Request) -> Optional[Tuple[Participant, Token]]:
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)

        return self.get_participant(validated_token), validated_token

    def authenticate_header(self, request: Request) -> str:
        return '{} realm="{}"'.format(
            AUTH_HEADER_TYPES[0],
            self.www_authenticate_realm,
        )

    def get_header(self, request: Request) -> bytes:
        header = request.META.get(JWT_SETTINGS.APPLICATION_HEADER_NAME)

        if isinstance(header, str):
            # Work around django test client oddness
            header = header.encode(HTTP_HEADER_ENCODING)

        return header

    def get_raw_token(self, header: bytes) -> Optional[bytes]:
        parts = header.split()

        if len(parts) == 0:
            # Empty AUTHORIZATION header sent
            return None

        if parts[0] not in AUTH_HEADER_TYPE_BYTES:
            # Assume the header does not contain a JSON web token
            return None

        if len(parts) != 2:
            raise AuthenticationFailed(
                _("Authorization header must contain two space-delimited values"),
                code="bad_authorization_header",
            )

        return parts[1]

    def get_validated_token(self, raw_token: bytes) -> Token:
        messages = []
        for PartToken in JWT_SETTINGS.PARTICIPANT_TOKEN_CLASS:
            try:
                return PartToken(raw_token)
            except TokenError as e:
                messages.append(
                    {
                        "token_class": PartToken.__name__,
                        "token_type": PartToken.token_type,
                        "message": e.args[0],
                    }
                )

        raise InvalidToken(
            {
                "detail": _("Given token not valid for any token type"),
                "messages": messages,
            }
        )

    def get_participant(self, validated_token: Token) -> Participant:
        try:
            participant_id = validated_token[JWT_SETTINGS.PARTICIPANT_ID_CLAIM]
        except KeyError:
            raise InvalidToken(
                _("Token contained no recognizable participant identification")
            )

        try:
            participant = Participant.objects.get(
                **{JWT_SETTINGS.PARTICIPANT_ID_FIELD: participant_id}
            )
        except Participant.DoesNotExist:
            raise AuthenticationFailed(
                _("Participant not found"), code="participant_not_found"
            )

        return participant
