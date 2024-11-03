from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Competition, Rule, Management, Applicant, Participant
from .exceptions import AlreadyApplied, NotApplied
from ..users.models import Profile, Account
from ..users.serializers import SimpleProfileSerializer


class RuleListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        rules = [Rule(**item) for item in validated_data]
        return Rule.objects.bulk_create(rules)


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = ["content", "added_at", "depth", "order"]
        read_only_fields = ["added_at", "depth"]
        extra_kwargs = {"order": {"required": True}}
        list_serializer_class = RuleListSerializer


class ManagementSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = Management
        fields = [
            "id",
            "profile",
            "competition",
            "nickname",
            "handle_rules",
            "handle_content",
            "handle_applicants",
            "handle_participants",
            "accepted",
        ]
        extra_kwargs = {
            "nickname": {"read_only": True},
            "accepted": {"read_only": True},
        }

    @extend_schema_field(SimpleProfileSerializer)
    def get_profile(self, obj):
        try:
            profile = Profile.objects.get(account=obj.account)
            return SimpleProfileSerializer(profile).data
        except Profile.DoesNotExist:
            return None


class ManagementNicknameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Management
        fields = ["id", "nickname"]


class CompetitionCreateSerializer(serializers.ModelSerializer):
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())
    managers = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = Competition
        fields = [
            "id",
            "title",
            "created_at",
            "creator",
            "introduction",
            "is_team_game",
            "managers",
        ]

    def create(self, validated_data):
        managers_data = validated_data.pop("managers")
        creator_username = self.validated_data["creator"].profile.username
        while creator_username in managers_data:
            managers_data.remove(creator_username)

        competition = Competition.objects.create(**validated_data)

        if managers_data is not None:
            account_ids = Profile.objects.filter(
                username__in=managers_data
            ).values_list("account_id", flat=True)
            Management.objects.bulk_create(
                [
                    Management(
                        account_id=account_id,
                        nickname=_(f"관리자 {idx}"),
                        competition=competition,
                    )
                    for idx, account_id in enumerate(account_ids, start=1)
                ]
            )

        return competition


class AddManagerOnCompetitionSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate_username(self, value):
        if not Profile.objects.filter(username=value).exists():
            raise serializers.ValidationError(_("존재하지 않는 유저명입니다."))
        return value

    def update(self, instance, validated_data):
        username = validated_data["username"]
        if instance.managers.filter(profile__username=username).exists():
            raise serializers.ValidationError(
                {"username": _("이미 매니저로 초대된 유저입니다.")}
            )
        num_of_managers = instance.managers.count()
        Management.objects.create(
            competition=instance,
            account=Account.objects.get(profile__username=username),
            nickname=f"매니저 {num_of_managers + 1}",
        )
        return instance


class SimpleCompetitionSerializer(serializers.ModelSerializer):
    creator = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = [
            "id",
            "title",
            "created_at",
            "creator",
            "status",
            "is_team_game",
            "introduction",
        ]
        read_only_fields = ["is_team_game"]

    @extend_schema_field(SimpleProfileSerializer)
    def get_creator(self, obj):
        try:
            profile = Profile.objects.get(account=obj.creator)
            return SimpleProfileSerializer(profile, context=self.context).data
        except Profile.DoesNotExist:
            return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, label in Competition.StatusChoices.choices:
            if data["status"] == key:
                data["status"] = label
                break
        return data


class CompetitionSerializer(SimpleCompetitionSerializer):
    is_manager = serializers.SerializerMethodField()
    num_of_participants = serializers.SerializerMethodField()
    num_of_applicants = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = [
            "id",
            "title",
            "created_at",
            "creator",
            "creator_nickname",
            "status",
            "content",
            "is_team_game",
            "num_of_participants",
            "num_of_applicants",
            "is_manager",
        ]
        read_only_fields = ["creator", "is_team_game", "status"]

    def get_is_manager(self, obj) -> bool:
        if self.context["request"].user == obj.creator:
            return True
        if self.context["request"].user in obj.managers.all():
            return True
        return False

    def get_num_of_participants(self, obj: Competition) -> int:
        return obj.participant_set.count()

    def get_num_of_applicants(self, obj: Competition) -> int:
        return obj.applicant_set.count()


class ApplicationSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Applicant
        fields = [
            "competition",
            "user",
            "access_id",
            "access_password",
            "email",
            "displayed_name",
            "hidden_name",
            "introduction",
            "applied_at",
        ]
        extra_kwargs = {"access_password": {"write_only": True}}

    def validate(self, data):
        competition_id = data["competition"]
        user = data["user"]
        access_id = data.get("access_id")
        access_password = data.get("access_password")
        if isinstance(user, AnonymousUser):
            if not access_id and not access_password:
                raise serializers.ValidationError(
                    {
                        "access_id": _("접속 아이디를 입력해주세요."),
                        "access_password": _("접속 비밀번호를 입력해주세요."),
                    }
                )
            if not access_id:
                raise serializers.ValidationError(
                    {"access_id": _("접속 아이디를 입력해주세요.")}
                )
            if not access_password:
                raise serializers.ValidationError(
                    {"access_password": _("접속 비밀번호를 입력해주세요.")}
                )

            if (
                Applicant.objects.filter(
                    competition_id=competition_id,
                    account_id__isnull=True,
                    access_id=access_id,
                ).exists()
                or Participant.objects.filter(
                    competition_id=competition_id,
                    account_id__isnull=True,
                    access_id=access_id,
                ).exists()
            ):
                raise serializers.ValidationError(
                    {"access_id": _("이미 존재하는 접속 아이디입니다.")}
                )
        else:
            data.pop("access_id", None)
            data.pop("access_password", None)
            if Competition.objects.filter(
                id=competition_id, creator_id=user.id
            ).exists():
                raise serializers.ValidationError(
                    _("대회 개최자는 참가 신청을 할 수 없습니다.")
                )
            authenticated_applicant_ids = Applicant.objects.filter(
                competition_id=competition_id, account_id__isnull=False
            ).values_list("account_id", flat=True)
            if user.id in authenticated_applicant_ids:
                raise AlreadyApplied()
        return data

    def create(self, validated_data):
        user = validated_data.pop("applicant_user")
        applicant = Applicant(**validated_data, account_id=user.id)
        applicant.set_password(validated_data.get("access_password"))
        applicant.save()
        return applicant


class ApplicantSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    profile = serializers.SerializerMethodField()

    class Meta:
        model = Applicant
        fields = [
            "id",
            "user",
            "profile",
            "competition",
            "access_id",
            "access_password",
            "email",
            "displayed_name",
            "hidden_name",
            "introduction",
            "applied_at",
        ]
        extra_kwargs = {
            "access_password": {"write_only": True},
            "access_id": {"write_only": True},
            "competition": {"write_only": True},
        }
        read_only_fields = [
            "id",
            "email",
            "displayed_name",
            "hidden_name",
            "introduction",
            "applied_at",
        ]

    def validate(self, data):
        user = data["user"]
        competition_id = data.get("competition", None)
        access_id = data.get("access_id", None)
        access_password = data.get("access_password", None)

        if isinstance(user, AnonymousUser):
            if not competition_id:
                raise serializers.ValidationError(_("알 수 없는 요청입니다."))
            if not access_id:
                raise serializers.ValidationError(
                    {"access_id": _("접속 아이디를 입력해주세요.")}
                )
            if not access_password:
                raise serializers.ValidationError(
                    {"access_password": _("접속 비밀번호를 입력해주세요.")}
                )
            try:
                applicant = Applicant.objects.get(
                    access_id=access_id, competition_id=competition_id
                )
                if not applicant.check_password(access_password):
                    raise serializers.ValidationError(
                        {"access_password": _("접속 비밀번호를 확인해주세요.")}
                    )
            except Applicant.DoesNotExist:
                raise NotApplied()
            return applicant

        try:
            applicant = Applicant.objects.get(
                competition_id=competition_id, account_id=user.id
            )
        except Applicant.DoesNotExist:
            raise NotApplied()
        return applicant

    @extend_schema_field(SimpleProfileSerializer)
    def get_profile(self, obj):
        if not obj.account:
            return None
        try:
            profile = Profile.objects.get(account=obj.account)
            return SimpleProfileSerializer(profile).data
        except Profile.DoesNotExist:
            return None


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = "__all__"
