from django.db import models


# Create your models here.
class MemberCostShare(models.Model):
    objectType = models.CharField(max_length=200)
    objectId = models.CharField(max_length=200)
    copay = models.IntegerField()
    _org = models.CharField(max_length=200)
    deductible = models.IntegerField()


class Service(models.Model):
    objectType = models.CharField(max_length=200)
    objectId = models.CharField(max_length=200)
    _org = models.CharField(max_length=200)
    name = models.CharField(max_length=200)


class PlanService(models.Model):
    objectType = models.CharField(max_length=200)
    objectId = models.CharField(max_length=200)
    _org = models.CharField(max_length=200)
    linkedService = Service()
    planerviceCostShares = MemberCostShare()

