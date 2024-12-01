from typing import List

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (
    IsAuthenticatedOrReadOnly,
    IsAuthenticated,
    AllowAny,
)
from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework_simplejwt.views import TokenViewBase

from .models import Competition, Management, Applicant, Participant
from .serializers import (
    CompetitionSerializer,
    CompetitionCreateSerializer,
    SimpleCompetitionSerializer,
    ManagementSerializer,
    AddManagerOnCompetitionSerializer,
    ApplicationSerializer,
    ApplicantSerializer,
    ParticipantSerializer,
    ManagerPermissionsSerializer,
)
from .permissions import IsCreator, ManagementPermission

JWT_SETTINGS = getattr(settings, "SIMPLE_JWT", {})


class ParticipantAccessTokenView(TokenViewBase):
    _serializer_class = JWT_SETTINGS.get("PARTICIPANT_ACCESS_TOKEN_SERIALIZER")


class ApplicationViewSet(viewsets.GenericViewSet):
    queryset = Applicant.objects.all()
    serializer_class = ApplicantSerializer
    permission_classes = [AllowAny]

    @action(methods=["POST"], detail=False)
    def check(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=False, serializer_class=ApplicationSerializer)
    def register(self, request):
        serializer = ApplicationSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": _("참가 신청을 완료했습니다.")}, status=status.HTTP_200_OK
        )


class CompetitionViewSet(viewsets.GenericViewSet, mixins.DestroyModelMixin):
    queryset = Competition.objects.all()
    serializer_class = CompetitionSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action == "create":
            return CompetitionCreateSerializer
        return self.serializer_class

    def create(self, request):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": _("새 대회가 생성됐습니다.")}, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        competition = self.get_object()
        serializer = self.get_serializer(competition, context={"request": request})
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        competition = self.get_object()
        serializer = self.get_serializer(competition, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=True,
        serializer_class=SimpleCompetitionSerializer,
        permission_classes=[AllowAny],
    )
    def preview(self, request, pk=None):
        competition = self.get_object()
        serializer = SimpleCompetitionSerializer(
            competition, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(responses=SimpleCompetitionSerializer(many=True))
    @action(
        methods=["GET"],
        detail=False,
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        my_competitions = self.queryset.filter(creator=request.user).order_by(
            "-created_at"
        )
        page = self.paginate_queryset(my_competitions)
        if page is not None:
            serializer = SimpleCompetitionSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = SimpleCompetitionSerializer(
            my_competitions, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        methods=["POST"],
        detail=True,
        serializer_class=AddManagerOnCompetitionSerializer,
        permission_classes=[IsCreator],
    )
    def invite_managers(self, request, pk=None):
        competition = self.get_object()
        serializer = AddManagerOnCompetitionSerializer(
            competition, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            data={"detail": _("매니저가 추가됐습니다.")}, status=status.HTTP_200_OK
        )


class ManagementViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.DestroyModelMixin
):
    serializer_class = ManagementSerializer
    permission_classes = [ManagementPermission]

    def get_queryset(self):
        return Management.objects.filter(competition__id=self.kwargs["competition_pk"])

    def get_permission_classes(self):
        if self.action == "create":
            return [IsCreator]
        return self.permission_classes

    def partial_update(self, request, pk=None):
        management = self.get_object()
        serializer = self.get_serializer(management, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)

    @action(
        methods=["GET"], detail=False, serializer_class=ManagerPermissionsSerializer
    )
    def me(self, request, competition_pk=None):
        queryset = self.get_queryset()
        management = get_object_or_404(queryset, account_id=request.user.id)
        serializer = ManagerPermissionsSerializer(
            management, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class ApplicantViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.DestroyModelMixin
):
    queryset = Applicant.objects.all()
    serializer_class = ApplicantSerializer
    permission_classes = [ManagementPermission]

    def get_queryset(self):
        return Applicant.objects.filter(competition__id=self.kwargs["competition_pk"])

    @extend_schema(request=List[int])
    @action(detail=False, methods=["POST"])
    def accept(self, request, competition_pk=None):
        applicant_ids = request.data
        applicants = self.get_queryset().filter(id__in=applicant_ids)
        num_of_participant = Participant.objects.filter(
            competition_id=competition_pk
        ).count()
        new_participants = []
        for i, applicant in enumerate(applicants, start=1):
            new_participants.append(
                Participant(
                    account=applicant.account,
                    competition=applicant.competition,
                    access_id=applicant.access_id,
                    access_password=applicant.access_password,
                    email=applicant.email,
                    displayed_name=applicant.displayed_name,
                    hidden_name=applicant.hidden_name,
                    introduction=applicant.introduction,
                    order=num_of_participant + i,
                )
            )
        Participant.objects.bulk_create(new_participants)
        applicants.delete()
        return Response(
            {"detail": f"{len(new_participants)}명의 참가자들이 추가됐습니다."},
            status=status.HTTP_200_OK,
        )


class ParticipantViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    queryset = Participant.objects.all()
    serializer_class = ParticipantSerializer
    permission_classes = [ManagementPermission]

    def get_queryset(self):
        return Participant.objects.filter(competition_id=self.kwargs["competition_pk"])
