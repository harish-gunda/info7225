import json
from rest_framework.views import APIView
from .serializers import PlanSerializer, PatchSerializer
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
import hashlib
from rest_framework.permissions import IsAuthenticated
from elasticsearch import Elasticsearch
from kafka import KafkaProducer
from kafka import KafkaConsumer
import os

# Single node via URL
es = Elasticsearch(
    "https://localhost:9200",
    ca_certs="/Users/harish/Downloads/elasticsearch-8.7.0/config/certs/http_ca.crt",
    basic_auth=("elastic", "A9sj3xj+v25dL2C1SDyu")
)
producer = KafkaProducer(bootstrap_servers='localhost:9092', api_version=(0,11,5))


def index_helper(payload):
    plan = payload
    plan['plan_join'] = "plan"
    es.index(index='plan_index', body=plan, id=plan['objectId'])

    planCostShares = payload["planCostShares"]
    planCostShares['plan_join'] = {"name": "planCostShares", "parent": plan['objectId']}
    es.index(index='plan_index', body=planCostShares, id=planCostShares['objectId'], routing=plan['objectId'])
    cache.set(planCostShares['objectId'], planCostShares)
    linkedPlanServices = payload['linkedPlanServices']
    for linkedPlanService in linkedPlanServices:
        linkedService = linkedPlanService['linkedService']
        planserviceCostShares = linkedPlanService['planserviceCostShares']
        linkedPlanService['plan_join'] = {"name": "linkedPlanService", "parent": plan['objectId']}
        es.index(index='plan_index', body=linkedPlanService, id=linkedPlanService['objectId'], routing=plan['objectId'])
        cache.set(linkedPlanService['objectId'], linkedPlanService)
        linkedService['plan_join'] = {"name": "linkedService", "parent": linkedPlanService['objectId']}
        es.index(index='plan_index', body=linkedService, id=linkedService['objectId'], routing=linkedPlanService['objectId'])
        cache.set(linkedService['objectId'], linkedService)
        planserviceCostShares['plan_join'] = {"name": "planserviceCostShares", "parent": linkedPlanService['objectId']}
        es.index(index='plan_index', body=planserviceCostShares, id=planserviceCostShares['objectId'], routing=linkedPlanService['objectId'])
        cache.set(planserviceCostShares['objectId'], planserviceCostShares)


# Plan create view
class PlanCreate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = PlanSerializer(data=request.data)
        if serializer.is_valid():
            encoded = json.dumps(request.data, sort_keys=True).encode('utf-8')
            # print(encoded)
            md5_hash = hashlib.md5(encoded)
            if cache.get(serializer.data['objectId']):
                return Response({"message": "An object exists with the given objectID"},
                                status=status.HTTP_409_CONFLICT)
            cache.set(serializer.data['objectId'], serializer.data)
            response = producer.send('FirstTopic', encoded)
            # print(response)
            producer.flush()
            consumer = KafkaConsumer('FirstTopic', bootstrap_servers='localhost:9092', api_version=(0, 11, 5),
                                     auto_offset_reset='earliest', group_id=None, consumer_timeout_ms=1000)
            for msg in consumer:
                payload = json.loads(msg.value)
                # print(payload)
                # es.index(index='contents', body=payload, id=serializer.data['objectId'])
                # print('Done')
                index_helper(payload)
            # print('Done2')
            consumer.close()
            return Response({"objectId": serializer.data['objectId']}, status=status.HTTP_201_CREATED,
                            headers={"Etag": md5_hash.hexdigest()})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Plan read view
class PlanRead(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, format=None):
        if cache.get(id):
            encoded = json.dumps(cache.get(id), sort_keys=True).encode('utf-8')
            md5_hash = hashlib.md5(encoded)
            if request.headers.get('if-none-match'):
                if md5_hash.hexdigest() == request.headers.get('if-none-match'):
                    return Response(status=status.HTTP_304_NOT_MODIFIED)
                else:
                    return Response({"message": "Invalid etag"}, status=status.HTTP_412_PRECONDITION_FAILED)
            return Response(cache.get(id), status=status.HTTP_200_OK, headers={"Etag": md5_hash.hexdigest()})
        return Response({"message": "Object Not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, id, format=None):
        if request.headers.get('if-none-match'):
            encoded = json.dumps(cache.get(id), sort_keys=True).encode('utf-8')
            md5_hash = hashlib.md5(encoded)
            if md5_hash.hexdigest() == request.headers.get('if-none-match'):
                if cache.get(id):
                    cache.delete(id)
                    es.delete_by_query(index='plan_index', body={"query": {"match_all": {}}})
                    return Response(status=status.HTTP_204_NO_CONTENT)
                return Response({"message": "Object Not found"}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"message": "Invalid etag"}, status=status.HTTP_412_PRECONDITION_FAILED)

        return Response({"message": "please provide etag"}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, id, format=None):
        if not cache.get(id):
            return Response({"message": "Object Not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.headers.get('if-none-match'):
            encoded = json.dumps(cache.get(id), sort_keys=True).encode('utf-8')
            md5_hash = hashlib.md5(encoded)
            if md5_hash.hexdigest() == request.headers.get('if-none-match'):
                serializer = PlanSerializer(data=request.data)
                if serializer.is_valid():
                    encoded = json.dumps(request.data, sort_keys=True).encode('utf-8')
                    print(encoded)
                    md5_hash = hashlib.md5(encoded)
                    if cache.get(serializer.data['objectId']):
                        cache.clear()
                        cache.set(serializer.data['objectId'], serializer.data)
                        es.delete_by_query(index='plan_index', body={"query": {"match_all": {}}})
                        index_helper(serializer.data)
                        return Response({"message": "resource updated successfully"}, status=status.HTTP_200_OK,
                                        headers={"Etag": md5_hash.hexdigest()})
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "Invalid etag"}, status=status.HTTP_412_PRECONDITION_FAILED)
        return Response({"message": "please provide etag"}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, id, format=None):
        if not cache.get(id):
            return Response({"message": "Object Not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.headers.get('if-none-match'):
            encoded = json.dumps(cache.get(id), sort_keys=True).encode('utf-8')
            md5_hash = hashlib.md5(encoded)
            if md5_hash.hexdigest() == request.headers.get('if-none-match'):
                serializer = PatchSerializer(data=request.data)
                if serializer.is_valid():
                    plan = cache.get(id)
                    new = []
                    for i in range(len(serializer.data['linkedPlanServices'])):
                        boo = True
                        for j in range(len(plan['linkedPlanServices'])):
                            if plan['linkedPlanServices'][j]['objectId'] == serializer.data['linkedPlanServices'][i]['objectId']:
                                plan['linkedPlanServices'][j] = serializer.data['linkedPlanServices'][i]
                                boo = False
                        if boo:
                            print(i)
                            new.append(i)
                    for i in new:
                        plan['linkedPlanServices'].append(serializer.data['linkedPlanServices'][i])
                    encoded = json.dumps(plan, sort_keys=True).encode('utf-8')
                    print(encoded)
                    md5_hash = hashlib.md5(encoded)
                    if cache.get(serializer.data['objectId']):
                        cache.set(serializer.data['objectId'], plan)
                        index_helper(plan)
                        return Response({"message": "resource updated successfully"}, status=status.HTTP_200_OK,
                                        headers={"Etag": md5_hash.hexdigest()})
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "Invalid etag"}, status=status.HTTP_412_PRECONDITION_FAILED)
        return Response({"message": "please provide etag"}, status=status.HTTP_400_BAD_REQUEST)




