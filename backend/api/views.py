from django.contrib.auth.models import Group, User
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import UserSerializer
from .models import UserInfo

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token["groups"] = user.groups

        return token

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

@api_view(['POST'])
def RegisterUser(request):
    userSerializer = UserSerializer(data=request.data)

    if userSerializer.is_valid():
        user = userSerializer.save()

        userInfo = UserInfo.objects.create(User=user)
        userInfo.save()

        return Response(userSerializer.data, status=201)
    else:
        return Response(userSerializer.errors, status=400)

# @api_view(['POST'])
# def RedeemAccessKey(request):
#

@api_view(['GET'])
def Profile(request, username):
    removedFields = ["password", "email"]
    user = get_object_or_404(User, username=username)
    userInfo = UserSerializer(user).data

    for field in removedFields:
        userInfo.pop(field)

    return Response(userInfo, status=200)