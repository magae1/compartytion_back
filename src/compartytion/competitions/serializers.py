from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Competition, Rule, Management
from ..users.models import Profile, Account
from ..users.serializers import SimpleProfileSerializer


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = ["next_rule", "content", "added_at"]
        read_only_fields = ["next_rule", "added_at"]


class ManagementSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    account = serializers.SlugRelatedField(
        many=False,
        slug_field="username",
        queryset=Account.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Management
        fields = [
            "profile",
            "account",
            "competition",
            "handle_rules",
            "handle_content",
            "handle_status",
            "handle_applicants",
            "handle_participants",
        ]
        extra_kwargs = {"competition": {"write_only": True}}

    @extend_schema_field(SimpleProfileSerializer)
    def get_profile(self, obj):
        try:
            profile = Profile.objects.get(account=obj.account)
            return SimpleProfileSerializer(profile).data
        except Profile.DoesNotExist:
            return None


class CompetitionCreateSerializer(serializers.ModelSerializer):
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())
    rule = RuleSerializer(many=False)

    class Meta:
        model = Competition
        fields = [
            "id",
            "title",
            "created_at",
            "creator",
            "rule",
            "introduction",
            "tournament",
            "content",
            "is_team_game",
        ]

    def create(self, validated_data):
        rule_data = validated_data.pop("rule")
        rule_obj = Rule.objects.create(**rule_data)
        return Competition.objects.create(**validated_data, rule=rule_obj)


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
    rule = RuleSerializer(many=False)
    managers = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = [
            "id",
            "title",
            "created_at",
            "creator",
            "managers",
            "status",
            "rule",
            "tournament",
            "content",
            "is_team_game",
        ]
        read_only_fields = ["creator", "is_team_game"]

    @extend_schema_field(SimpleProfileSerializer)
    def get_managers(self, obj):
        profiles = set()
        for m in obj.managers.all().select_related("profile"):
            profiles.add(m.profile)
        return SimpleProfileSerializer(profiles, many=True, context=self.context).data
