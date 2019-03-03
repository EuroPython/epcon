
from pytest import mark
from tests.common_tools import template_used


@mark.django_db
def test_get_homepage(client):
    url = '/'
    response = client.get(url)

    assert response.status_code == 200
    # TODO(artcz): make sure this works with a CMS setup
    assert template_used(response, 'ep19/bs/homepage/home.html')
    assert template_used(response, 'ep19/bs/homepage/_venue.html')
    assert template_used(response, 'ep19/bs/homepage/_sponsors.html')
    assert template_used(response, 'ep19/bs/homepage/_schedule_overview.html')
    assert template_used(response, 'ep19/bs/header/_with_jumbotron.html')
    assert b'EuroPython 2019' in response.content
