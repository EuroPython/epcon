import json

from django.contrib.sites.shortcuts import get_current_site
from django.core import mail
from django.test import Client
from django.test.client import RequestFactory
from django.urls import reverse

from pytest import mark

from conference.accounts import send_verification_email

from . import factories


@mark.django_db
def test_send_verification_email():
    user = factories.UserFactory()

    user.is_active = False
    user.save()

    request = RequestFactory()
    current_site = get_current_site(request)

    assert not mail.outbox  # sanity check

    send_verification_email(user, current_site)

    assert len(mail.outbox) == 1

    message = mail.outbox[0]
    assert len(message.recipients()) == 1
    assert message.recipients()[0] == user.email
    assert current_site.domain in message.body

@mark.django_db
def test_matrix_endpoint_ok():
    user = factories.UserFactory(password="mate_cafe_harina")

    PAYLOAD = {
        "user": {
        "id": f"@matrix.{user.username}:europython.eu",
        "password": "mate_cafe_harina"
      }
    }
    EXPECTED_SUCCESS = {
        "auth": {
            "success": True,
            "mxid": f"@matrix.{user.username}:europython.eu",
        }
    }
    client= Client()

    r = client.post(reverse("accounts:matrix_auth"), PAYLOAD, content_type="application/json")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["auth"]["success"]
    assert response_data["auth"]["mxid"] == EXPECTED_SUCCESS["auth"]["mxid"]


@mark.django_db
def test_matrix_endpoint_denied():
    user = factories.UserFactory(password="mate_cafe_harina")

    PAYLOAD = {
        "user": {
        "id": f"@matrix.{user.username}:europython.eu",
        "password": "wrong_password"
      }
    }
    EXPECTED_ERROR = {
        "auth": {
            "success": False,
        }
    }
    client= Client()

    r = client.post(reverse("accounts:matrix_auth"), PAYLOAD, content_type="application/json")
    assert r.status_code == 200
    r.json() == EXPECTED_ERROR

@mark.django_db
def test_matrix_endpoint_profile():
    user = factories.UserFactory(password="mate_cafe_harina")

    PAYLOAD = {
        "user": {
        "id": f"@matrix.{user.username}:europython.eu",
        "password": "mate_cafe_harina"
      }
    }
    EXPECTED_SUCCESS = {
        "auth": {
            "success": True,
            "mxid": f"@matrix.{user.username}:europython.eu",
            "profile": {
                "display_name": f"{user.first_name} {user.last_name}",
                "three_pids": [
                    {
                        "medium": "email",
                        "address": user.email,
                    },
                ]
            }
        }
    }
    client= Client()

    r = client.post(reverse("accounts:matrix_auth"), PAYLOAD, content_type="application/json")
    assert r.status_code == 200
    assert r.json() == EXPECTED_SUCCESS
