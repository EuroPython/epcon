from pytest import mark
from django.urls import reverse
from conference.api import ApiError
from conference.models import TALK_STATUS
from .common_tools import (
    get_default_conference,
    make_user,
)
from .factories import (
    TalkFactory,
    TalkSpeakerFactory,
)


@mark.django_db
def test_non_post_error(client):
    payload = {'key': 'does not matter'}
    response = client.get(reverse('api:isauth'), payload,
                          content_type='Application/json')
    result = response.json()
    assert result['error'] == ApiError.BAD_REQUEST.value


@mark.django_db
def test_non_json_post_error(client):
    payload = {'key': 'does not matter'}
    response = client.post(reverse('api:isauth'), payload)
    result = response.json()
    assert result['error'] == ApiError.BAD_REQUEST.value


@mark.django_db
def test_user_does_not_exist(client):
    payload = {'email': 'does.not@exist.com', 'password': 'hahahaha'}
    response = client.post(reverse('api:isauth'), payload,
                           content_type='application/json')
    result = response.json()
    assert result['error'] == ApiError.AUTH_ERROR.value


@mark.django_db
def test_user_password_error(client):
    user = make_user(is_staff=False)
    payload = {'email': user.email, 'password': user.password + 'hahahaha'}
    response = client.post(reverse('api:isauth'), payload,
                           content_type='application/json')
    result = response.json()
    assert result['error'] == ApiError.AUTH_ERROR.value


@mark.django_db
def test_non_staff_non_speaker_user_auth_success(client):
    get_default_conference()
    user = make_user(is_staff=False)
    payload = {'email': user.email, 'password': 'password123'}
    response = client.post(reverse('api:isauth'), payload,
                           content_type='application/json')
    result = response.json()
    assert result['email'] == user.email
    assert result['first_name'] == user.first_name
    assert result['last_name'] == user.last_name
    assert result['is_staff'] is False
    assert result['is_speaker'] is False


@mark.django_db
def test_staff_non_speaker_user_auth_success(client):
    get_default_conference()
    user = make_user(is_staff=True)
    payload = {'email': user.email, 'password': 'password123'}
    response = client.post(reverse('api:isauth'), payload,
                           content_type='application/json')
    result = response.json()
    assert result['email'] == user.email
    assert result['first_name'] == user.first_name
    assert result['last_name'] == user.last_name
    assert result['is_staff'] is True
    assert result['is_speaker'] is False


@mark.django_db
def test_staff_speaker_user_auth_success(client):
    get_default_conference()
    user = make_user(is_staff=True)
    talk = TalkFactory(created_by=user, status=TALK_STATUS.accepted)
    TalkSpeakerFactory(talk=talk, speaker__user=user)

    payload = {'email': user.email, 'password': 'password123'}
    response = client.post(reverse('api:isauth'), payload,
                           content_type='application/json')
    result = response.json()
    assert result['email'] == user.email
    assert result['first_name'] == user.first_name
    assert result['last_name'] == user.last_name
    assert result['is_staff'] is True
    assert result['is_speaker'] is True


@mark.django_db
def test_staff_proposed_speaker_user_auth_success(client):
    get_default_conference()
    user = make_user(is_staff=True)
    talk = TalkFactory(created_by=user, status=TALK_STATUS.proposed)
    TalkSpeakerFactory(talk=talk, speaker__user=user)

    payload = {'email': user.email, 'password': 'password123'}
    response = client.post(reverse('api:isauth'), payload,
                           content_type='application/json')
    result = response.json()
    assert result['email'] == user.email
    assert result['first_name'] == user.first_name
    assert result['last_name'] == user.last_name
    assert result['is_staff'] is True
    assert result['is_speaker'] is False
