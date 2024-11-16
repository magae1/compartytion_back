from django.contrib.auth.models import AnonymousUser
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Competition, Rule, Management, Applicant, Participant
from .exceptions import AlreadyApplied, NotApplied, AlreadyBeParticipant, InvalidRequest
from ..users.models import Profile, Account
from ..users.serializers import SimpleAccountSerializer


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


class SimpleParticipantSerializer(serializers.ModelSerializer):
    account = SimpleAccountSerializer(many=False)

    class Meta:
        model = Participant
        fields = ["id", "account", "displayed_name", "order"]


class ParticipantSerializer(SimpleParticipantSerializer):
    class Meta:
        model = Participant
        fields = [
            "id",
            "account",
            "access_id",
            "access_password",
            "email",
            "displayed_name",
            "hidden_name",
            "introduction",
            "order",
            "joined_at",
            "last_login_at",
        ]
        extra_kwargs = {
            "access_id": {"write_only": True},
            "access_password": {"write_only": True},
            "email": {"write_only": True},
        }


class ManagementSerializer(serializers.ModelSerializer):
    account = SimpleAccountSerializer(many=False)

    class Meta:
        model = Management
        fields = [
            "id",
            "account",
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
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())
    usernames = serializers.ListField(child=serializers.CharField())

    def update(self, instance: Competition, validated_data):
        usernames = validated_data["usernames"]

        if instance.managers.filter(profile__username__in=usernames).exists():
            raise serializers.ValidationError(
                {"usernames": _("이미 초대된 관리자가 포함되어 있습니다.")}
            )

        num_of_managers = instance.managers.count()
        account_ids = Profile.objects.filter(username__in=usernames).values_list(
            "account_id", flat=True
        )

        Management.objects.bulk_create(
            [
                Management(
                    account_id=account_id,
                    nickname=_(f"관리자 {idx}"),
                    competition=instance,
                )
                for idx, account_id in enumerate(account_ids, start=num_of_managers + 1)
            ]
        )
        return instance


class SimpleCompetitionSerializer(serializers.ModelSerializer):
    creator = SimpleAccountSerializer(many=False)

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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, label in Competition.StatusChoices.choices:
            if data["status"] == key:
                data["status"] = label
                break
        return data


class CompetitionSerializer(SimpleCompetitionSerializer):
    creator = SimpleAccountSerializer(many=False)
    is_manager = serializers.SerializerMethodField()
    num_of_participants = serializers.SerializerMethodField()
    num_of_applicants = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()

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
            "participants",
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

    @extend_schema_field(
        serializers.ListSerializer(child=SimpleParticipantSerializer())
    )
    def get_participants(self, obj: Competition):
        participants = Participant.objects.filter(competition=obj)
        return [SimpleParticipantSerializer(instance=p).data for p in participants]


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
        competition = data["competition"]
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
                    competition=competition,
                    account_id__isnull=True,
                    access_id=access_id,
                ).exists()
                or Participant.objects.filter(
                    competition=competition,
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
                id=competition.id, creator_id=user.id
            ).exists():
                raise InvalidRequest(_("대회 개최자는 참가 신청을 할 수 없습니다."))
            authenticated_applicant_ids = Applicant.objects.filter(
                competition=competition, account_id__isnull=False
            ).values_list("account_id", flat=True)
            if user.id in authenticated_applicant_ids:
                raise AlreadyApplied()
            authenticated_participant_ids = Participant.objects.filter(
                competition=competition, account_id__isnull=False
            ).values_list("account_id", flat=True)
            if user.id in authenticated_participant_ids:
                raise AlreadyBeParticipant()
        return data

    def create(self, validated_data):
        user = validated_data.pop("user")
        if isinstance(user, AnonymousUser):
            applicant = Applicant(**validated_data)
            applicant.set_password(validated_data.get("access_password"))
        else:
            applicant = Applicant(**validated_data, account_id=user.id)
        applicant.save()
        return applicant


class ApplicantSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    account = SimpleAccountSerializer(many=False, read_only=True)

    class Meta:
        model = Applicant
        fields = [
            "id",
            "user",
            "account",
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
                raise InvalidRequest(_("잘못된 요청입니다."))
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
