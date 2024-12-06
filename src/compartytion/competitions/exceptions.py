from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


class AlreadyApplied(APIException):
    status_code = 409
    default_detail = _("이미 신청한 대회입니다.")
    default_code = "AlreadyApplied"


class AlreadyBeParticipant(APIException):
    status_code = 409
    default_detail = _("이미 참여 중인 대회입니다.")
    default_code = "AlreadyBeParticipant"


class NotApplied(APIException):
    status_code = 404
    default_detail = _("신청 정보를 찾을 수 없습니다.")
    default_code = "NotApplied"


class InvalidRequest(APIException):
    status_code = 400
    default_code = "InvalidRequest"
