
from pytest import mark
from tests.common_tools import template_used


@mark.django_db
def test_get_homepage(client):
    url = '/'
    response = client.get(url)

    assert response.status_code == 200
    assert template_used(response, 'ep19/homepage.html')
    assert b'EuroPython 2019' in response.content
    # TODO: check if we can check if it's a jinja template
