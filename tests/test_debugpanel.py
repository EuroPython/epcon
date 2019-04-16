from django.conf import settings
from conference.models import Conference


def test_index(admin_client):
    """
    Basic test to see if it even works.
    """
    url = "/nothing-to-see-here/"
    HTTP_OK_200 = 200
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
    )

    respnse = admin_client.get(url)
    assert respnse.status_code == HTTP_OK_200
