from rest_framework.request import Request
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Competition


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
    def has_permission(self, request: Request, view) -> bool:
        competition_id: str = view.kwargs["competition_pk"]
        try:
            competition = Competition.objects.get(id=competition_id)
            if request.method in SAFE_METHODS:
                return (
                    request.user == competition.creator
                    or request.user in competition.managers.filter(accepted=True)
                )
            return request.user == competition.creator
        except Competition.DoesNotExist:
            return False
