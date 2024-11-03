from typing import Dict
from rest_framework.request import Request
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Competition, Management


class IsCreator(BasePermission):
    def has_object_permission(self, request: Request, view, obj: Competition) -> bool:
        return obj.creator == request.user


class IsManager(BasePermission):
    def has_object_permission(self, request: Request, view, obj: Competition) -> bool:
        return request.user in obj.managers.all()


class IsParticipant(BasePermission):
    def has_object_permission(self, request: Request, view, obj: Competition) -> bool:
        return request.user in obj.participant_set.all()


class ManagementPermission(BasePermission):
    _handle_method_name = None

    def has_permission(self, request: Request, view) -> bool:
        if not request.user.is_authenticated:
            return False

        competition_id: str = view.kwargs["competition_pk"]
        try:
            competition = Competition.objects.get(id=competition_id)
            if request.user == competition.creator:
                return True
            if request.method in SAFE_METHODS:
                return Management.objects.filter(
                    competition=competition, account=request.user
                ).exists()
            else:
                if not self._handle_method_name:
                    return False
                attrs: Dict = {
                    "competition": competition,
                    self._handle_method_name: True,
                    "account": request.user,
                }
                return Management.objects.filter(**attrs).exists()
        except Competition.DoesNotExist:
            return False


class ApplicantManagementPermission(ManagementPermission):
    _handle_method_name = "handle_applicants"
