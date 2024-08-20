from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

from .models import Competition, Management
from .serializers import (
    CompetitionSerializer,
    CompetitionCreateSerializer,
    SimpleCompetitionSerializer,
    ManagementSerializer,
)
from .permissions import IsCreator


class CompetitionViewSet(viewsets.GenericViewSet, mixins.DestroyModelMixin):
    queryset = Competition.objects.all()
    serializer_class = CompetitionSerializer

    def get_permissions(self):
        if self.action == "retrieve":
            permission_classes = [IsCreator]
        else:
            permission_classes = [IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]

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
        return Response(serializer.data)

    @action(methods=["GET"], detail=True, serializer_class=SimpleCompetitionSerializer)
    def preview(self, request, pk=None):
        competition = self.get_object()
        serializer = SimpleCompetitionSerializer(
            competition, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        methods=["GET"],
        detail=False,
        serializer_class=SimpleCompetitionSerializer,
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
        methods=["GET", "PATCH"],
        detail=True,
        serializer_class=ManagementSerializer,
        permission_classes=[IsCreator],
    )
    def managers(self, request, pk=None):
        if request.method == "GET":
            competition = self.get_object()
            managements = Management.objects.filter(competition=competition)
            serializer = ManagementSerializer(managements, many=True)
            return Response(data=serializer.data)
        if request.method == "PATCH":
            competition = self.get_object()
            queryset = Management.objects.filter(
                competition=competition
            ).select_related("account")
            username = request.data.pop("account", None)
            request.data["competition"] = pk
            management = get_object_or_404(queryset, account__username=username)
            serializer = ManagementSerializer(
                management, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"detail": _("매니저 권한이 변경됐습니다.")})
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        methods=["POST"],
        detail=True,
        serializer_class=ManagementSerializer,
        permission_classes=[IsCreator],
    )
    def add_manager(self, request, pk=None):
        request.data["competition"] = pk
        serializer = ManagementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_201_CREATED)

    @action(
        methods=["POST"],
        detail=True,
        serializer_class=ManagementSerializer,
        permission_classes=[IsCreator],
    )
    def delete_manager(self, request, pk=None):
        competition = self.get_object()
        queryset = Management.objects.filter(competition=competition).select_related(
            "account"
        )
        username = request.data.pop("account", None)
        management = get_object_or_404(queryset, account__username=username)
        management.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
