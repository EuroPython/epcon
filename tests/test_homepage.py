
from pytest import mark
from tests.common_tools import template_used


@mark.django_db
def test_get_homepage(client):
    url = '/'
    response = client.get(url)

    assert response.status_code == 200
    assert template_used(response, 'ep19/bs/homepage/home.html')
    assert template_used(response, 'ep19/bs/homepage/_venue.html')
    assert template_used(response, 'ep19/bs/homepage/_sponsors.html')
    assert template_used(response, 'ep19/bs/homepage/_schedule_overview.html')
    assert template_used(response, 'ep19/bs/header/_with_jumbotron.html')
    assert b'EuroPython 2019' in response.content


@mark.django_db
def test_homepage_contains_googleanalytics(client):
    url = '/'
    response = client.get(url)
    assert response.status_code == 200

    EPCON_2019_GA_ID = 'UA-60323107-5'
    # NOTE(artcz) this should probably go into a variable, but good enough for
    assert EPCON_2019_GA_ID in response.content.decode()
