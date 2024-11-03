"""
URL configuration for compartytion_back project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_nested.routers import SimpleRouter, NestedSimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView
from debug_toolbar.toolbar import debug_toolbar_urls
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from ..users.views import AuthViewSet, AccountViewSet, ProfileViewSet
from ..competitions.views import (
    CompetitionViewSet,
    ManagementViewSet,
    ApplicationViewSet,
    ParticipantAccessTokenView,
    ApplicantViewSet,
)

router = SimpleRouter()
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"accounts", AccountViewSet, basename="accounts")
router.register(r"profiles", ProfileViewSet, basename="profiles")
router.register(r"competitions", CompetitionViewSet, basename="competitions")
router.register(r"applications", ApplicationViewSet, basename="applications")

competition_router = NestedSimpleRouter(router, r"competitions", lookup="competition")
competition_router.register(r"managers", ManagementViewSet, basename="competitions")
competition_router.register(r"applicants", ApplicantViewSet, basename="applicants")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path(
        "api/token/participant/access/",
        ParticipantAccessTokenView.as_view(),
        name="participant-access-token",
    ),
    path("api/", include(router.urls)),
    path("api/", include(competition_router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
    ] + debug_toolbar_urls()
