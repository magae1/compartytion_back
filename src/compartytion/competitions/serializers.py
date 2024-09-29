from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Competition, Rule, Management
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
    num_of_participants = serializers.SerializerMethodField()
    num_of_applicants = serializers.SerializerMethodField()

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
            "num_of_participants",
            "num_of_applicants",
        ]
        read_only_fields = ["is_team_game"]

    @extend_schema_field(SimpleProfileSerializer)
    def get_creator(self, obj):
        try:
            profile = Profile.objects.get(account=obj.creator)
            return SimpleProfileSerializer(profile, context=self.context).data
        except Profile.DoesNotExist:
            return None

    @extend_schema_field(int)
    def get_num_of_participants(self, obj):
        return obj.participant_set.count()

    @extend_schema_field(int)
    def get_num_of_applicants(self, obj):
        return obj.applicant_set.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, label in Competition.StatusChoices.choices:
            if data["status"] == key:
                data["status"] = label
                break
        return data


class CompetitionSerializer(SimpleCompetitionSerializer):
    is_manager = serializers.SerializerMethodField()

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

    @extend_schema_field(bool)
    def get_is_manager(self, obj):
        if self.context["request"].user == obj.creator:
            return True
        if self.context["request"].user in obj.managers.all():
            return True
        return False
