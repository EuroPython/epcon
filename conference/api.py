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
from hashlib import md5
from django.conf.urls import url as re_path
from django.contrib.auth.hashers import check_password as django_check_password
from django.contrib.auth.hashers import is_password_usable
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
from pycon.settings import MATRIX_AUTH_API_DEBUG as DEBUG
from pycon.settings import MATRIX_AUTH_API_ALLOWED_IPS as ALLOWED_IPS
from pycon.settings import SECRET_KEY


# Error Codes
class ApiError(Enum):
    WRONG_METHOD = 1
    AUTH_ERROR = 2
    INPUT_ERROR = 3
    UNAUTHORIZED = 4
    WRONG_SCHEME = 5
    BAD_REQUEST = 6


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


# Checkers
def request_checker(checker, error_msg):
    """
    Generic sanity check decorator on views.

    It accepts two parameters:
        `checker`: a function that accepts a request and returns True if valid
        `error_msg`: what to return as error message if request is invalid

    In case of invalid requests, it returns a BAD_REQUEST error.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            if not checker(request):
                return _error(ApiError.BAD_REQUEST, error_msg)
            return fn(request, *args, **kwargs)
        return wrapper
    return decorator


# Ensure that the view is called via an HTTPS request and return a JSON error
# payload if not. If DEBUG = True, it has no effect.
ensure_https_in_ops = request_checker(
    lambda r: DEBUG or r.is_secure(), 'please use HTTPS'
)

# We use this instead of the bult-in decorator to return a JSON error
# payload instead of a simple 405.
ensure_post = request_checker(lambda r: r.method == 'POST', 'please use POST')

ensure_json_content_type = request_checker(
    lambda r: r.content_type == 'application/json', 'please send JSON'
)


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


def check_user_password(user, password):
    # Two options: either our User has a valid password, in which case we do
    # check it, or not, in which case we check it against the generated passwd.
    if not is_password_usable(user.password):
        return password == generate_matrix_password(user)
    return django_check_password(password, user.password)


def get_assigned_tickets(user, conference):
    return Ticket.objects.filter(
        Q(fare__conference=conference.code)
        & Q(frozen=False)                   # i.e. the ticket was not cancelled
        & Q(orderitem__order___complete=True)       # i.e. they paid
        & Q(user=user)                              # i.e. assigned to user
    )


def is_speaker(user, conference):
    # A speaker is a user with at least one accepted talk in the current
    # conference.
    try:
        speaker = user.speaker
    except Speaker.DoesNotExist:
        return False
    return TalkSpeaker.objects.filter(
        speaker=speaker,
        talk__conference=conference.code,
        talk__status='accepted'
    ).count() > 0


def generate_matrix_password(user):
    """
    Create a temporary password for `user` to that they can login into our
    matrix chat server using their email address and that password. This is
    only needed for social auth users since they do not have a valid password
    in our database.

    The generated passowrd is not stored anywhere.
    """
    def n_base_b(n, b, nums='0123456789abcdefghijklmnopqrstuvwxyz'):
        """Return `n` in base `b`."""

        return ((n == 0) and nums[0]) or \
            (n_base_b(n // b, b, nums).lstrip(nums[0]) + nums[n % b])

    encoded = md5(str(user.email + SECRET_KEY).encode()).hexdigest()
    n = int(encoded, 16)
    return n_base_b(n, 36)


@csrf_exempt
@ensure_post
@ensure_https_in_ops
@ensure_json_content_type
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
    if not check_user_password(profile.user, data['password']):
        return _error(ApiError.AUTH_ERROR, 'authentication error')

    conference = Conference.objects.current()
    payload = {
        "username": profile.user.username,
        "first_name": profile.user.first_name,
        "last_name": profile.user.last_name,
        "email": profile.user.email,
        "is_staff": profile.user.is_staff,
        "is_speaker": is_speaker(profile.user, conference),
        "is_active": profile.user.is_active,
        "is_minor": profile.is_minor,
        "tickets": [
            {"fare_name": t.fare.name, "fare_code": t.fare.code}
            for t in get_assigned_tickets(profile.user, conference)
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
