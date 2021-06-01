from pytest import mark

from tests import factories
from tests import common_tools
from tests.common_tools import (
    make_user,
    create_talk_for_user,
    get_default_conference,
    template_used)
from conference import user_panel
from conference import models

STERAMS_1 = [
    {
        "title": "Holy Grail",
        "fare_codes": ["TRCC", "TRCP", "TRSC", "TRSP", "TRVC", "TRVP"],
        "url": "https://www.youtube.com/embed/EEIk7gwjgIM"
    }
]

def create_streamset():
    get_default_conference()
    stream_set = factories.StreamSetFactory(
        streams=repr(STERAMS_1).replace('\'', '"')
    )
    stream_set.save()

@mark.django_db
def test_streamset(user_client):
    create_streamset()

@mark.django_db
def test_streamset_without_ticket(user_client):
    create_streamset()

    # User without ticket
    data = user_panel.get_streams_for_current_conference(user_client.user)
    #print (data)
    assert not data['streams']
    assert 'reload_timeout_seconds' in data

@mark.django_db
def test_streamset_with_ticket(user_client):
    create_streamset()

    # User with view-only ticket
    common_tools.setup_conference_with_typical_fares()
    fare = models.Fare.objects.get(code='TRVC')
    ticket = common_tools.create_valid_ticket_for_user_and_fare(
        user_client.user, fare=fare)
    ticket.save()
    data = user_panel.get_streams_for_current_conference(user_client.user)
    #print (data)
    assert len(data['streams']) == 1
    tracks = data['streams'][0]
    assert tracks['title'] == 'Holy Grail'
    assert tracks['url'] == 'https://www.youtube.com/embed/EEIk7gwjgIM'
    assert 'reload_timeout_seconds' in data
    assert data['reload_timeout_seconds'] > 3600 # factory sets the end_date to now + 1 hour
