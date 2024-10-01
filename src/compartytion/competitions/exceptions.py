from rest_framework.exceptions import APIException


class AlreadyApplied(APIException):
    status_code = 409
    default_detail = "이미 신청한 대회입니다."
    default_code = "AlreadyApplied"
