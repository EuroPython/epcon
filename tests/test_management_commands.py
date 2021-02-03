import json
from io import StringIO

from django.core.management import call_command

import pytest
from freezegun import freeze_time

from conference.models import TALK_STATUS
from tests.common_tools import (
    create_talk_for_user,
    get_default_conference,
    create_user,
    create_valid_ticket_for_user_and_fare,
)

pytestmark = pytest.mark.django_db


def test_talk_abstracts():
    stdout = StringIO()
    conference = get_default_conference()
    create_talk_for_user(user=None)

    call_command("talk_abstracts", conference.code, stdout=stdout)

    abstracts = json.loads(stdout.getvalue())
    assert "talk" in abstracts
    assert len(abstracts["talk"]) == 1


# Creating an order tags the order with the year number of the current year right now.
@freeze_time("2021-02-02")
def test_ticket_profiles():
    stdout = StringIO()
    conference = get_default_conference()
    user = create_user()
    ticket = create_valid_ticket_for_user_and_fare(user=user)

    call_command("ticket_profiles", conference.code, "--status=all", stdout=stdout)

    profiles = json.loads(stdout.getvalue())
    assert len(profiles) == 1
    profile = profiles[0]
    assert profile["name"] == user.first_name
    assert profile["surname"] == user.last_name
    assert profile["fare_code"] == ticket.fare.code


def test_speakers_list():
    stdout = StringIO()
    conference = get_default_conference()
    create_talk_for_user(user=None, status=TALK_STATUS.accepted)

    call_command("speaker_list", conference.code, stdout=stdout)

    assert "1 speakers in total" in stdout.getvalue()


def test_speakers_csv():
    stdout = StringIO()
    conference = get_default_conference()
    user = create_user()
    create_talk_for_user(user=user, status=TALK_STATUS.accepted)

    call_command("speakers_csv", conference.code, stdout=stdout)

    # Check there is a header line and a data line in the output (two non-empty lines)
    assert len([line for line in stdout.getvalue().split("\n") if line]) == 2
    assert f"{user.first_name} {user.last_name}" in stdout.getvalue()
