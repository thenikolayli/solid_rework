from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.shortcuts import redirect, resolve_url
from django.conf import settings

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import UserSerializer, jwtrequired
from .models import UserInfo, AccessKey, EventLogged
from .util.keyclublogging import log_event, log_meeting
import jwt, json


# function to create a response with updated user data and new jwt token pair cookies
def GetNewTokenPairResponse(new_refresh_token):
    new_access_token = new_refresh_token.access_token
    user_id = jwt.decode(str(new_access_token), settings.SECRET_KEY, algorithms=["HS256"])["user_id"]
    user = User.objects.get(pk=user_id)
    user_data = UserSerializer(user).data
    user_data.pop("password")
    new_jwt_token = {
        "access_token": str(new_access_token),
        "refresh_token": str(new_refresh_token),
    }

    response = Response(user_data, status=status.HTTP_200_OK)
    response.set_cookie("jwt_token", json.dumps(new_jwt_token),
                        httponly=settings.JWT_HTTPONLY,
                        secure=False, #settings.JWT_SECURE,
                        samesite=settings.JWT_SAMESITE,
                        max_age=settings.JWT_COOKIE_MAX_AGE,
                        path="/", domain=settings.JWT_DOMAIN)

    return response

# view that creates a new jwt token pair cookies and returns them with user data
@api_view(['POST'])
def LoginUser(request):
    username = request.data["username"]
    password = request.data["password"]

    user = authenticate(request, username=username, password=password)

    if user is not None:
        new_refresh_token = RefreshToken.for_user(user)
        return GetNewTokenPairResponse(new_refresh_token)
    return Response("Invalid credentials", status=status.HTTP_401_UNAUTHORIZED)

# view that creates a new user
@api_view(['POST'])
def RegisterUser(request):
    userSerializer = UserSerializer(data=request.data)

    if userSerializer.is_valid():
        if userSerializer.validated_data["username"] == settings.DJANGO_SUPERUSER_USERNAME:
            userSerializer.validated_data["is_superuser"] = True
            userSerializer.validated_data["is_staff"] = True
        user = userSerializer.save()

        userInfo = UserInfo.objects.create(User=user)
        userInfo.save()

        return Response(userSerializer.data, status=status.HTTP_201_CREATED)
    else:
        return Response(userSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

# view that returns new jwt token pair cookies with updated user data
@api_view(['GET'])
def UpdateRefreshToken(request):
    jwt_token = request.COOKIES.get("jwt_token")

    if jwt_token:
        refresh_token = json.loads(jwt_token)["refresh_token"]
        try:
            new_refresh_token = RefreshToken(refresh_token)
            return GetNewTokenPairResponse(new_refresh_token)
        except InvalidToken:
            return Response("invalid credentials", status=status.HTTP_401_UNAUTHORIZED)
    return Response("no refresh token", status=status.HTTP_404_NOT_FOUND)

# view that removes the jwt token pair cookies
@api_view(['GET'])
def LogoutUser(request):
    response = Response("logging out", status=status.HTTP_200_OK)
    response.delete_cookie("jwt_token", path="/", domain=settings.JWT_DOMAIN)
    response.delete_cookie("google_api_token", path="/", domain=settings.JWT_DOMAIN)

    return response


# view that returns a redirect uri to the google consent screen
@api_view(['POST'])
@jwtrequired(settings.VITE_KEYCLUB_GROUP_NAME) # requires user to be logged in and be in the key club bot group
def GoogleAuthorize(request):
    flow = InstalledAppFlow.from_client_config(client_config=settings.GOOGLE_CLIENT_CONFIG, scopes=settings.GOOGLE_SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI)
    redirect_uri, state = flow.authorization_url(prompt="consent") # uri with consent screen
    request.session["state"] = state

    return Response(redirect_uri, status=status.HTTP_200_OK)

# view that creates Google API credentials and saves them as a cookie and redirects the user to the Key Club Log page
@api_view(['GET'])
@jwtrequired(settings.VITE_KEYCLUB_GROUP_NAME)
def GoogleOauthCallback(request):
    code = request.GET["code"]
    state = request.session["state"]
    flow = InstalledAppFlow.from_client_config(client_config=settings.GOOGLE_CLIENT_CONFIG, scopes=settings.GOOGLE_SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI, state=state)
    token = json.dumps(flow.fetch_token(code=code))

    response = redirect(settings.KEYCLUB_LOG_URL)
    response.set_cookie("google_api_token", token,
                        httponly=settings.JWT_HTTPONLY,
                        secure=settings.JWT_SECURE,
                        samesite=settings.JWT_SAMESITE,
                        path="/", domain=settings.JWT_DOMAIN)
    return response

# view that takes in url to Key Club event signup Google Doc or Key Club meeting attendance Google Sheets and logs it
@api_view(["POST"])
@jwtrequired(settings.VITE_KEYCLUB_GROUP_NAME)
def KeyClubLogEvent(request):
    google_api_token = request.COOKIES.get("google_api_token")
    response = Response()
    # check if access token is there, if so, build credentials and check if they're valid, attempt to refresh, otherwise through error
    if not google_api_token:
        return Response("log in with google", status=status.HTTP_401_UNAUTHORIZED)

    google_api_token = json.loads(google_api_token)
    credentials = Credentials(token=google_api_token["access_token"], refresh_token=google_api_token["refresh_token"], token_uri=settings.GOOGLE_TOKEN_URI, client_id=settings.GOOGLE_CLIENT_ID, client_secret=settings.GOOGLE_CLIENT_SECRET)

    # token validity check and refresh
    if not credentials.valid: # if credentials exist but are invalid
        if credentials.expired and credentials.refresh_token: # if they're expired but have a refresh token, refresh them
            credentials.refresh(GoogleRequest())  # refreshes
            new_token = json.dumps({"access_token": credentials.token, # creates a new token with the new info
                                    "refresh_token": credentials.refresh_token,
                                    "scope": google_api_token["scope"]
                                    })
            response.set_cookie("google_api_token", new_token,
                                httponly=settings.JWT_HTTPONLY,
                                secure=settings.JWT_SECURE,
                                samesite=settings.JWT_SAMESITE,
                                path="/", domain=settings.JWT_DOMAIN) # updated google_api_token cookie
        else:
            return Response("unable to refresh credentials, log in with google", status=status.HTTP_401_UNAUTHORIZED)

    # logs the event
    document_id = request.data.get("link")
    hours_multiplier = request.data.get("hours_multiplier")
    log_event_response = log_event(document_id, hours_multiplier, credentials)

    if log_event_response.get("error"):
        response.status_code = status.HTTP_400_BAD_REQUEST
        response.data = log_event_response.get("error")
        return response

    # creates db entry to represent logged event
    hours_logged = 0
    hours_not_logged = 0
    people_attended = 0

    # volunteers logged
    if log_event_response.get("logged"):
        for volunteer_logged, data in log_event_response.get("logged").items():
            hours_logged += data
            people_attended += 1

    # volunteers not logged
    if log_event_response.get("not_logged"):
        for volunteer_not_logged, data in log_event_response.get("not_logged").items():
            hours_not_logged += data
            people_attended += 1

    # saves db entry
    EventLogged(event_title=log_event_response.get("event_title"),
                 hours_logged=hours_logged,
                 hours_not_logged=hours_not_logged,
                 people_attended=people_attended).save()

    response.status_code = status.HTTP_200_OK
    response.data = log_event_response
    return response

# view that takes in url to Key Club meeting attendance form responses Google Sheet and logs it
@api_view(["POST"])
@jwtrequired(settings.VITE_KEYCLUB_GROUP_NAME)
def KeyClubLogMeeting(request):
    google_api_token = request.COOKIES.get("google_api_token")
    response = Response()
    # check if access token is there, if so, build credentials and check if they're valid, attempt to refresh, otherwise through error
    if not google_api_token:
        return Response("log in with google", status=status.HTTP_401_UNAUTHORIZED)

    google_api_token = json.loads(google_api_token)
    credentials = Credentials(token=google_api_token["access_token"], refresh_token=google_api_token["refresh_token"], token_uri=settings.GOOGLE_TOKEN_URI, client_id=settings.GOOGLE_CLIENT_ID, client_secret=settings.GOOGLE_CLIENT_SECRET)

    # token validity check and refresh
    if not credentials.valid: # if credentials exist but are invalid
        if credentials.expired and credentials.refresh_token: # if they're expired but have a refresh token, refresh them
            credentials.refresh(GoogleRequest())  # refreshes
            new_token = json.dumps({"access_token": credentials.token, # creates a new token with the new info
                                    "refresh_token": credentials.refresh_token,
                                    "scope": google_api_token["scope"]
                                    })
            response.set_cookie("google_api_token", new_token,
                                httponly=settings.JWT_HTTPONLY,
                                secure=settings.JWT_SECURE,
                                samesite=settings.JWT_SAMESITE,
                                path="/", domain=settings.JWT_DOMAIN) # updated google_api_token cookie
        else:
            return Response("unable to refresh credentials, log in with google", status=status.HTTP_401_UNAUTHORIZED)

    # logs the event
    document_id = request.data.get("link")
    first_name_col = request.data.get("first_name_col")
    last_name_col = request.data.get("last_name_col")
    meeting_length = request.data.get("meeting_length")
    meeting_title = request.data.get("meeting_title")
    log_event_response = log_meeting(document_id, first_name_col, last_name_col, meeting_length, meeting_title, credentials)

    if log_event_response.get("error"):
        response.status_code = status.HTTP_400_BAD_REQUEST
        response.data = log_event_response.get("error")
        return response

    # creates db entry to represent logged event
    hours_logged = 0
    hours_not_logged = 0
    people_attended = 0

    # volunteers logged
    if log_event_response.get("logged"):
        for volunteer_logged, data in log_event_response.get("logged").items():
            hours_logged += data
            people_attended += 1

    # volunteers not logged
    if log_event_response.get("not_logged"):
        for volunteer_not_logged, data in log_event_response.get("not_logged").items():
            hours_not_logged += data
            people_attended += 1

    # saves db entry
    EventLogged(event_title=log_event_response.get("event_title"),
                 hours_logged=hours_logged,
                 hours_not_logged=hours_not_logged,
                 people_attended=people_attended).save()

    response.status_code = status.HTTP_200_OK
    response.data = log_event_response
    return response


# view that activates an access key and adds the user to the group in the access key
@api_view(['POST'])
@jwtrequired()
def ActivateAccessKey(request):
    access_key = request.data.get("access_key")
    token = request.COOKIES.get("jwt_token")
    access_token = json.loads(token)["access_token"]
    payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
    user = User.objects.get(pk=payload["user_id"])

    try:
        access_key = AccessKey.objects.get(Code=access_key)
        group = access_key.Group
        group.user_set.add(user)
        access_key.delete()

        return Response("access key activated successfully, check your settings to view your roles",
                        status=status.HTTP_200_OK)
    except AccessKey.DoesNotExist:
        return Response("access key does not exist", status=status.HTTP_404_NOT_FOUND)

# @api_view(['GET'])
# def Profile(request, username):
#     removedFields = ["password", "email"]
#     user = get_object_or_404(User, username=username)
#     userInfo = UserSerializer(user).data
#
#     for field in removedFields:
#         userInfo.pop(field)
#
#     return Response(userInfo, status=status.HTTP_200_OK)