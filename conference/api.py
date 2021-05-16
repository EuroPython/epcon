"""
Matrix/Synapse custom authentication provider backend.

This allows a Matrix/Synapse installation to use a custom backaned (not part of
this API) to authenticate users against epcon database.

The main (and currently the only) endpoint is

    /api/v1/isauth

For more information about developing a custom auth backend for matrix/synapse
please refer to https://github.com/matrix-org/synapse/blob/master/docs/\
    password_auth_providers.md
"""
from enum import Enum
import json
from functools import wraps
from django.conf.urls import url as re_path
from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from conference.models import (
    AttendeeProfile,
    Conference,
    Speaker,
    TalkSpeaker,
    Ticket,
)

DEBUG = True
# Only these IPs can connect to the API
ALLOWED_IPS = []


# Error Codes
class ApiError(Enum):
    WRONG_METHOD = 1
    AUTH_ERROR = 2
    INPUT_ERROR = 3
    UNAUTHORIZED = 4
    WRONG_SCHEME = 5


def _error(error: ApiError, msg: str) -> JsonResponse:
    return JsonResponse({
        'error': error.value,
        'message': f'{error.name}: {msg}'
    })


def get_client_ip(request) -> str:
    """
    Return the client IP.

    This is a best effort way of fetching the client IP which does not protect
    against spoofing and hich tries to understand some proxying.

    This should NOT be relied upon for serius stuff.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def ensure_https_in_ops(fn):
    """
    Ensure that the view is called via an HTTPS request and return a JSON error
    payload if not.

    If DEBUG = True, it has no effect.
    """
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not DEBUG and not request.is_secure():
            return _error(ApiError.WRONG_SCHEME, 'please use HTTPS')
        return fn(request, *args, **kwargs)
    return wrapper


def ensure_post(fn):
    # We use this instead of the bult-in decorator to return a JSON error
    # payload instead of a simple 405.
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.method != 'POST':
            return _error(ApiError.WRONG_SCHEME, 'please use POST')
        return fn(request, *args, **kwargs)
    return wrapper


def restrict_client_ip_to_allowed_list(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        # This is really a best effort attempt at detecting the client IP. It
        # does NOT handle IP spooding or any similar attack.
        best_effort_ip = get_client_ip(request)
        if ALLOWED_IPS and best_effort_ip not in ALLOWED_IPS:
            return _error(ApiError.UNAUTHORIZED, 'you are not authorized here')
        return fn(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@ensure_post
@ensure_https_in_ops
@restrict_client_ip_to_allowed_list
def isauth(request):
    """
    Return whether or not the given email and password (sent via POST) are
    valid. If they are indeed valid, return the number and type of tickets
    assigned to the user, together with some other user metadata (see below).

    Input via POST:
    {
        "email": str,
        "password": str (not encrypted)
    }

    Output (JSON)
    {
        "username": str,
        "first_name": str,
        "last_name": str,
        "email": str,
        "is_staff": bool,
        "is_speaker": bool,
        "is_active": bool,
        "is_minor": bool,
        "tickets": [{"fare_name": str, "fare_code": str}*]
    }

    Tickets, if any, are returned only for the currently active conference and
    only if ASSIGNED to the user identified by `email`.

    In case of any error (including but not limited to if either email or
    password are incorrect/unknown), return
    {
        "message": str,
        "error": int
    }
    """
    required_fields = {'email', 'password'}

    try:
        data = json.loads(request.body)
    except json.decoder.JSONDecodeError as ex:
        return _error(ApiError.INPUT_ERROR, ex.msg)

    if not isinstance(data, dict) or not required_fields.issubset(data.keys()):
        return _error(ApiError.INPUT_ERROR,
                      'please provide credentials in JSON format')

    # First, let's find the user/account profile given the email address
    try:
        profile = AttendeeProfile.objects.get(user__email=data['email'])
    except AttendeeProfile.DoesNotExist:
        return _error(ApiError.AUTH_ERROR, 'unknown user')

    # Is the password OK?
    if not check_password(data['password'], profile.user.password):
        return _error(ApiError.AUTH_ERROR, 'authentication error')

    # Get the tickets **assigned** to the user
    conference = Conference.objects.current()

    tickets = Ticket.objects.filter(
        Q(fare__conference=conference.code)
        & Q(frozen=False)                   # i.e. the ticket was not cancelled
        & Q(orderitem__order___complete=True)       # i.e. they paid
        & Q(user=profile.user)                      # i.e. assigned to user
    )

    # A speaker is a user with at least one accepted talk in the current
    # conference.
    try:
        speaker = profile.user.speaker
    except Speaker.DoesNotExist:
        is_speaker = False
    else:
        is_speaker = TalkSpeaker.objects.filter(
            speaker=speaker,
            talk__conference=conference.code,
            talk__status='accepted'
        ).count() > 0

    payload = {
        "username": profile.user.username,
        "first_name": profile.user.first_name,
        "last_name": profile.user.last_name,
        "email": profile.user.email,
        "is_staff": profile.user.is_staff,
        "is_speaker": is_speaker,
        "is_active": profile.user.is_active,
        "is_minor": profile.is_minor,
        "tickets": [
            {"fare_name": t.fare.name, "fare_code": t.fare.code}
            for t in tickets
        ]
    }

    # Just a little nice to have thing when debugging: we can send in the POST
    # payload, all the fields that we want to override in the answer and they
    # will just be passed through regardless of what is in the DB. We just
    # remove the password to be on the safe side.
    if DEBUG:
        data.pop('password')
        payload.update(data)
    return JsonResponse(payload)


urlpatterns = [
    re_path(r"^v1/isauth/$", isauth, name="isauth"),
]
