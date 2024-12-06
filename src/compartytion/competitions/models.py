from uuid import uuid4
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Competition(models.Model):
    class StatusChoices(models.IntegerChoices):
        RECRUIT = 0, _("모집중")
        READY = 1, _("모집 마감")
        PLAY = 2, _("진행중")
        DONE = 3, _("완료")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(_("대회명"), max_length=255)
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True, editable=False)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("개최자"),
        null=True,
        on_delete=models.SET_NULL,
        related_name="creator",
    )
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Management",
        verbose_name=_("관리자들"),
        related_name="managers",
    )
    status = models.PositiveSmallIntegerField(
        _("상태"), default=StatusChoices.RECRUIT, choices=StatusChoices
    )
    introduction = models.TextField(
        _("대회 소개"), null=True, blank=True, max_length=500
    )
    tournament = models.JSONField(_("토너먼트"), default=dict, null=True)
    content = models.JSONField(_("내용"), default=dict, null=True)
    is_team_game = models.BooleanField(_("팀 게임 여부"), default=False)

    class Meta:
        verbose_name = _("대회")
        verbose_name_plural = _("대회들")
        get_latest_by = "created_at"


class RuleManager(models.Manager):
    def get_latest(self, competition_id: str):
        return self.raw(
            "SELECT * FROM competitions_rule AS r1 WHERE r1.competition_id = %s AND r1.depth = (SELECT MAX(r2.depth) FROM competitions_rule AS r2  WHERE r1.order = r2.order) ORDER BY r1.order",
            [competition_id],
        )


class Rule(models.Model):
    content = models.CharField(_("내용"))
    order = models.PositiveSmallIntegerField(_("순서"))
    depth = models.PositiveSmallIntegerField(_("깊이"))
    competition = models.ForeignKey(
        Competition,
        verbose_name=_("대회"),
        on_delete=models.CASCADE,
        related_name="rules",
    )
    added_at = models.DateTimeField(_("갱신일"), editable=False)

    objects = RuleManager()

    class Meta:
        verbose_name = _("규칙")
        verbose_name_plural = _("규칙들")
        ordering = ["order"]


class Management(models.Model):
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("계정"),
        on_delete=models.CASCADE,
        editable=False,
    )
    competition = models.ForeignKey(
        Competition, verbose_name=_("대회"), on_delete=models.PROTECT, editable=False
    )
    nickname = models.CharField(_("닉네임"), max_length=30)
    is_creator = models.BooleanField(_("개최자 여부"), default=False)
    handle_rules = models.BooleanField(_("규칙 변경 가능 여부"), default=False)
    handle_content = models.BooleanField(_("내용 변경 가능 여부"), default=False)
    handle_applicants = models.BooleanField(_("신청자 관리 가능 여부"), default=False)
    handle_participants = models.BooleanField(_("참가자 관리 가능 여부"), default=False)
    accepted = models.BooleanField(_("승락 여부"), default=False)

    class Meta:
        verbose_name = _("대회 관리자")
        verbose_name_plural = _("대회 관리자들")
        constraints = [
            models.UniqueConstraint(
                fields=["account", "competition"], name="unique_manager_per_competition"
            ),
        ]


class Team(models.Model):
    competition = models.ForeignKey(
        Competition, verbose_name=_("대회"), on_delete=models.PROTECT
    )
    order = models.PositiveSmallIntegerField(_("순서"))
    name = models.CharField(_("팀명"), max_length=30)
    introduction = models.TextField(_("팀 소개글"), null=True, blank=True)

    class Meta:
        verbose_name = _("참가팀")
        verbose_name_plural = _("참가팀들")
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "order"], name="unique_team_order"
            ),
        ]


class AbstractPlayer(models.Model):
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("계정"),
        null=True,
        on_delete=models.SET_NULL,
    )
    competition = models.ForeignKey(
        Competition, verbose_name=_("대회"), on_delete=models.PROTECT
    )
    access_id = models.CharField(_("접속 아이디"), blank=True, null=True, max_length=40)
    access_password = models.CharField(
        _("접속 비밀번호"), blank=True, null=True, max_length=255
    )
    email = models.EmailField(_("이메일"), null=True)
    displayed_name = models.CharField(_("공개 이름"), max_length=30)
    hidden_name = models.CharField(_("비공개 이름"), max_length=30)
    introduction = models.TextField(_("소개글"), null=True, blank=True, max_length=255)

    class Meta:
        abstract = True

    def set_password(self, raw_password):
        self.access_password = make_password(raw_password)

    def check_password(self, raw_password) -> bool:
        return check_password(raw_password, self.access_password)


class Participant(AbstractPlayer):
    team = models.ForeignKey(
        Team, verbose_name=_("소속 팀"), null=True, on_delete=models.SET_NULL
    )
    order = models.PositiveSmallIntegerField(_("순서"))
    joined_at = models.DateTimeField(_("참가일"), auto_now_add=True, editable=False)
    last_login_at = models.DateTimeField(_("최근 접속일"), auto_now_add=True)

    class Meta:
        verbose_name = _("대회 참가자")
        verbose_name_plural = _("대회 참가자들")
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "order"], name="unique_participant_order"
            )
        ]

    def update_last_login(self):
        self.last_login_at = timezone.now()
        self.save()


class Applicant(AbstractPlayer):
    applied_at = models.DateTimeField(_("신청일"), auto_now_add=True, editable=False)

    class Meta:
        verbose_name = _("대회 신청자")
        verbose_name_plural = _("대회 신청자들")
