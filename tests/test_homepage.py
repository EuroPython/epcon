
from pytest import mark
from tests.common_tools import template_used, is_using_jinja2_template


@mark.django_db
def test_get_homepage(client):
    url = '/'
    response = client.get(url)

    assert response.status_code == 200
    assert template_used(response, 'ep19/homepage.html')
    assert b'EuroPython 2019' in response.content
    assert is_using_jinja2_template(response)
