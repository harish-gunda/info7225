import json
from rest_framework.views import APIView
from .serializers import PlanSerializer
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
import hashlib


# Plan create view
class PlanCreate(APIView):
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
    def get(self, request, id, format=None):
        if cache.get(id):
            if request.headers.get('ETag'):
                encoded = json.dumps(cache.get(id), sort_keys=True).encode('utf-8')
                md5_hash = hashlib.md5(encoded)
                if md5_hash.hexdigest() == request.headers.get('ETag'):
                    return Response(status=status.HTTP_304_NOT_MODIFIED)
            return Response(cache.get(id), status=status.HTTP_200_OK)
        return Response({"message": "Object Not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, requet, id, format=None):
        if cache.get(id):
            cache.delete(id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"message": "Object Not found"}, status=status.HTTP_404_NOT_FOUND)