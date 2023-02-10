from rest_framework import serializers
from .models import MemberCostShare, PlanService, Service


class MemberCostShare(serializers.ModelSerializer):
    class Meta:
        model = MemberCostShare
        fields = '__all__'


class PlanServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanService
        fields = '__all__'


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'


class LinkedPlanServicesSerializer(serializers.Serializer):
    linkedService = Service()
    planserviceCostShares = MemberCostShare()
    _org = serializers.CharField()
    objectId = serializers.CharField()
    objectType = serializers.CharField()


class PlanSerializer(serializers.Serializer):
    _org = serializers.CharField()
    objectId = serializers.CharField()
    objectType = serializers.CharField()
    planType = serializers.CharField()
    creationDate = serializers.CharField()
    planCostShares = MemberCostShare()
    linkedPlanServices = serializers.ListField(child=LinkedPlanServicesSerializer())
