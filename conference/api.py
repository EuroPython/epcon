from enum import Enum
import json
from django.conf.urls import url as re_path
from django.contrib.auth.hashers import check_password
from django.db.models import Q, Case, When, Value, BooleanField
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


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@csrf_exempt
def isauth(request):
    """
    Return whether or not the given email and password (sent via POST) are
    valid. If they are indeed valid, return the number and type of tickets
    assigned to the user.

    Input via POST:
    {
        "email": email,
        "password": password (not encrypted)
    }
    Output (JSON)
    {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,

        "tickets": [{"fare_name": fare_name, "fare_code": fare_code}*]
    }

    Tickets, if any, are returned only for the currently active conference and
    only if ASSIGNED to email.

    If either email or password are incorrect/unknown, return
    {
        "message": "error message as string",
        "error": error_code
    }
    """
    best_effort_ip = get_client_ip(request)
    if ALLOWED_IPS and best_effort_ip not in ALLOWED_IPS:
        return _error(ApiError.UNAUTHORIZED, 'you are not authorized here')

    if request.scheme != 'https':
        return _error(ApiError.WRONG_SCHEME, 'please use HTTPS')

    if request.method != 'POST':
        return _error(ApiError.WRONG_METHOD, 'please use POST')

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

    # Get the tickets
    conference = Conference.objects.current()
    tickets = Ticket.objects.filter(
        Q(fare__conference=conference.code)
        & Q(frozen=False)
        & Q(orderitem__order___complete=True)
        & Q(user=profile.user)
    ).annotate(
        is_buyer=Case(
            When(orderitem__order__user__pk=profile.user.assopy_user.pk,
                 then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )

    # A speaker is a user with at least one accepted talk in the current
    # conference.
    try:
        speaker = profile.user.speaker
    except Speaker.DoesNotExist:
        is_speaker = False
    else:
        talkspeakers = TalkSpeaker.objects.filter(
            speaker=speaker, talk__conference=conference.code
        )
        is_speaker = len([None for ts in talkspeakers
                          if ts.talk.status == 'accepted']) != 0

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

    if DEBUG:
        data.pop('password')
        payload.update(data)
    return JsonResponse(payload)


urlpatterns = [
    re_path(r"^v1/isauth/$", isauth, name="isauth"),
]
