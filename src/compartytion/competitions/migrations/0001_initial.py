# Generated by Django 5.1.2 on 2024-12-01 08:05

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Competition",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="대회명")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="생성일"),
                ),
                (
                    "status",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "모집중"),
                            (1, "모집 마감"),
                            (2, "진행중"),
                            (3, "완료"),
                        ],
                        default=0,
                        verbose_name="상태",
                    ),
                ),
                (
                    "introduction",
                    models.TextField(
                        blank=True, max_length=500, null=True, verbose_name="대회 소개"
                    ),
                ),
                (
                    "tournament",
                    models.JSONField(default=dict, null=True, verbose_name="토너먼트"),
                ),
                (
                    "content",
                    models.JSONField(default=dict, null=True, verbose_name="내용"),
                ),
                (
                    "is_team_game",
                    models.BooleanField(default=False, verbose_name="팀 게임 여부"),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="creator",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="개최자",
                    ),
                ),
            ],
            options={
                "verbose_name": "대회",
                "verbose_name_plural": "대회들",
                "get_latest_by": "created_at",
            },
        ),
        migrations.CreateModel(
            name="Applicant",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "access_id",
                    models.CharField(
                        blank=True, max_length=40, null=True, verbose_name="접속 아이디"
                    ),
                ),
                (
                    "access_password",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="접속 비밀번호",
                    ),
                ),
                (
                    "email",
                    models.EmailField(max_length=254, null=True, verbose_name="이메일"),
                ),
                (
                    "displayed_name",
                    models.CharField(max_length=30, verbose_name="공개 이름"),
                ),
                (
                    "hidden_name",
                    models.CharField(max_length=30, verbose_name="비공개 이름"),
                ),
                (
                    "introduction",
                    models.TextField(
                        blank=True, max_length=255, null=True, verbose_name="소개글"
                    ),
                ),
                (
                    "applied_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="신청일"),
                ),
                (
                    "account",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="계정",
                    ),
                ),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="competitions.competition",
                        verbose_name="대회",
                    ),
                ),
            ],
            options={
                "verbose_name": "대회 신청자",
                "verbose_name_plural": "대회 신청자들",
            },
        ),
        migrations.CreateModel(
            name="Management",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nickname", models.CharField(max_length=30, verbose_name="닉네임")),
                (
                    "is_creator",
                    models.BooleanField(default=False, verbose_name="개최자 여부"),
                ),
                (
                    "handle_rules",
                    models.BooleanField(
                        default=False, verbose_name="규칙 변경 가능 여부"
                    ),
                ),
                (
                    "handle_content",
                    models.BooleanField(
                        default=False, verbose_name="내용 변경 가능 여부"
                    ),
                ),
                (
                    "handle_applicants",
                    models.BooleanField(
                        default=False, verbose_name="신청자 관리 가능 여부"
                    ),
                ),
                (
                    "handle_participants",
                    models.BooleanField(
                        default=False, verbose_name="참가자 관리 가능 여부"
                    ),
                ),
                (
                    "accepted",
                    models.BooleanField(default=False, verbose_name="승락 여부"),
                ),
                (
                    "account",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="계정",
                    ),
                ),
                (
                    "competition",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="competitions.competition",
                        verbose_name="대회",
                    ),
                ),
            ],
            options={
                "verbose_name": "대회 관리자",
                "verbose_name_plural": "대회 관리자들",
            },
        ),
        migrations.AddField(
            model_name="competition",
            name="managers",
            field=models.ManyToManyField(
                related_name="managers",
                through="competitions.Management",
                to=settings.AUTH_USER_MODEL,
                verbose_name="관리자들",
            ),
        ),
        migrations.CreateModel(
            name="Rule",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("content", models.CharField(verbose_name="내용")),
                ("order", models.PositiveSmallIntegerField(verbose_name="순서")),
                ("depth", models.PositiveSmallIntegerField(verbose_name="깊이")),
                (
                    "added_at",
                    models.DateTimeField(editable=False, verbose_name="갱신일"),
                ),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rules",
                        to="competitions.competition",
                        verbose_name="대회",
                    ),
                ),
            ],
            options={
                "verbose_name": "규칙",
                "verbose_name_plural": "규칙들",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("order", models.PositiveSmallIntegerField(verbose_name="순서")),
                ("name", models.CharField(max_length=30, verbose_name="팀명")),
                (
                    "introduction",
                    models.TextField(blank=True, null=True, verbose_name="팀 소개글"),
                ),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="competitions.competition",
                        verbose_name="대회",
                    ),
                ),
            ],
            options={
                "verbose_name": "참가팀",
                "verbose_name_plural": "참가팀들",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="Participant",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "access_id",
                    models.CharField(
                        blank=True, max_length=40, null=True, verbose_name="접속 아이디"
                    ),
                ),
                (
                    "access_password",
                    models.CharField(
                        blank=True,
                        max_length=255,
                        null=True,
                        verbose_name="접속 비밀번호",
                    ),
                ),
                (
                    "email",
                    models.EmailField(max_length=254, null=True, verbose_name="이메일"),
                ),
                (
                    "displayed_name",
                    models.CharField(max_length=30, verbose_name="공개 이름"),
                ),
                (
                    "hidden_name",
                    models.CharField(max_length=30, verbose_name="비공개 이름"),
                ),
                (
                    "introduction",
                    models.TextField(
                        blank=True, max_length=255, null=True, verbose_name="소개글"
                    ),
                ),
                ("order", models.PositiveSmallIntegerField(verbose_name="순서")),
                (
                    "joined_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="참가일"),
                ),
                (
                    "last_login_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="최근 접속일"),
                ),
                (
                    "account",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="계정",
                    ),
                ),
                (
                    "competition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="competitions.competition",
                        verbose_name="대회",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="competitions.team",
                        verbose_name="소속 팀",
                    ),
                ),
            ],
            options={
                "verbose_name": "대회 참가자",
                "verbose_name_plural": "대회 참가자들",
                "ordering": ["order"],
            },
        ),
        migrations.AddConstraint(
            model_name="management",
            constraint=models.UniqueConstraint(
                fields=("account", "competition"), name="unique_manager_per_competition"
            ),
        ),
        migrations.AddConstraint(
            model_name="team",
            constraint=models.UniqueConstraint(
                fields=("competition", "order"), name="unique_team_order"
            ),
        ),
        migrations.AddConstraint(
            model_name="participant",
            constraint=models.UniqueConstraint(
                fields=("competition", "order"), name="unique_participant_order"
            ),
        ),
    ]
