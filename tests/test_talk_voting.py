from datetime import date, timedelta

from django.conf import settings
from django.urls import reverse

from conference.models import Conference

from tests.common_tools import (
    redirects_to,
    template_used,
)
from tests.factories import TicketFactory


def test_new_talk_voting_is_inaccessible_to_unauthenticated_users(db, client):
    url = reverse("talk_voting:talks")
    response = client.get(url)

    assert response.status_code == 302
    assert redirects_to(response, "/accounts/login/")


def test_new_talk_voting_is_unavailable_to_user_without_tickets(
    db, user_client
):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_NAME,
        voting_start=date.today() - timedelta(days=1),
        voting_end=date.today() + timedelta(days=1),
    )
    url = reverse("talk_voting:talks")

    response = user_client.get(url)
    assert response.status_code == 200
    assert template_used(
        response, "conference/talk_voting/voting_is_unavailable.html"
    )


def test_new_talk_voting_can_be_access_with_user_who_has_tickets(
    db, user_client
):
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_NAME,
        voting_start=date.today() - timedelta(days=1),
        voting_end=date.today() + timedelta(days=1),
    )
    url = reverse("talk_voting:talks")
    TicketFactory(user=user_client.user)

    response = user_client.get(url)
    assert response.status_code == 200
    assert template_used(
        response, "conference/talk_voting/voting.html"
    )
