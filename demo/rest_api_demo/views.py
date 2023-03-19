import json
from rest_framework.views import APIView
from .serializers import PlanSerializer, PatchSerializer
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
import hashlib
from rest_framework.permissions import IsAuthenticated


# Plan create view
class PlanCreate(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = PlanSerializer(data=request.data)
        if serializer.is_valid():
            encoded = json.dumps(request.data, sort_keys=True).encode('utf-8')
            print(encoded)
            md5_hash = hashlib.md5(encoded)
            if cache.get(serializer.data['objectId']):
                return Response({"message": "An object exists with the given objectID"},
                                status=status.HTTP_409_CONFLICT)
            cache.set(serializer.data['objectId'], serializer.data)
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
                        cache.set(serializer.data['objectId'], serializer.data)
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
                        return Response({"message": "resource updated successfully"}, status=status.HTTP_200_OK,
                                        headers={"Etag": md5_hash.hexdigest()})
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "Invalid etag"}, status=status.HTTP_412_PRECONDITION_FAILED)
        return Response({"message": "please provide etag"}, status=status.HTTP_400_BAD_REQUEST)


