from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Competition, Rule, Management
from ..users.models import Profile
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
            "profile",
            "competition",
            "handle_rules",
            "handle_content",
            "handle_status",
            "handle_applicants",
            "handle_participants",
        ]

    @extend_schema_field(SimpleProfileSerializer)
    def get_profile(self, obj):
        try:
            profile = Profile.objects.get(account=obj.account)
            return SimpleProfileSerializer(profile).data
        except Profile.DoesNotExist:
            return None


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
                    Management(account_id=id, competition=competition)
                    for id in account_ids
                ]
            )

        return competition


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
