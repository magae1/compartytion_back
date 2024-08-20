from django.utils import timezone
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
    rules = serializers.ListField(child=serializers.CharField())
    managers = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = Competition
        fields = [
            "id",
            "title",
            "created_at",
            "creator",
            "rules",
            "introduction",
            "tournament",
            "content",
            "is_team_game",
            "managers",
        ]

    def create(self, validated_data):
        rule_data = validated_data.pop("rules")
        managers_data = validated_data.pop("managers")
        creator_username = self.validated_data["creator"].username
        while creator_username in managers_data:
            managers_data.remove(creator_username)

        competition = Competition.objects.create(**validated_data)

        if managers_data is not None:
            account_objs = Account.objects.filter(username__in=managers_data).values(
                "id"
            )
            for i in account_objs:
                print(i["id"])
            Management.objects.bulk_create(
                [
                    Management(account_id=a["id"], competition=competition)
                    for a in account_objs
                ]
            )

        now = timezone.now()
        rules = [
            Rule(
                order=i,
                depth=0,
                added_at=now,
                competition=competition,
                content=rule_content,
            )
            for i, rule_content in enumerate(rule_data)
        ]
        Rule.objects.bulk_create(rules)
        return competition


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
            "content",
            "is_team_game",
            "num_of_participants",
            "num_of_applicants",
        ]
        read_only_fields = ["creator", "is_team_game", "status"]

    def get_num_of_participants(self, obj):
        return obj.participant_set.count()

    def get_num_of_applicants(self, obj):
        return obj.applicant_set.count()
