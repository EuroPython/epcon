import pytest

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from tests.common_tools import template_used
from conference.models import Conference, News
from conference.tests.factories.conference import ConferenceFactory
from conference.tests.factories.fare import SponsorFactory


def test_get_homepage(db, client):
    url = "/"
    response = client.get(url)

    assert response.status_code == 200
    assert template_used(response, "ep19/bs/homepage/home.html")
    assert template_used(response, "ep19/bs/homepage/_venue.html")
    assert template_used(response, "ep19/bs/homepage/_sponsors.html")
    assert template_used(response, "ep19/bs/homepage/_schedule_overview.html")
    assert template_used(response, "ep19/bs/header/_with_jumbotron.html")
    assert b"EuroPython 2019" in response.content


def test_homepage_contains_last_3_news_for_current_conference(db, client):
    conference = ConferenceFactory()

    News.objects.create(
        conference=conference,
        title="First news",
        content="First news content",
        status=News.STATUS.PUBLISHED,
        published_date=timezone.now() - timedelta(days=4),
    )
    News.objects.create(
        conference=conference,
        title="Second news",
        content="Second news content",
        status=News.STATUS.PUBLISHED,
        published_date=timezone.now() - timedelta(days=3),
    )
    News.objects.create(
        conference=conference,
        title="Third news",
        content="Third news content",
        status=News.STATUS.PUBLISHED,
        published_date=timezone.now() - timedelta(days=2),
    )
    News.objects.create(
        conference=conference,
        title="Fourth news",
        content="Fourth news content",
        status=News.STATUS.PUBLISHED,
        published_date=timezone.now() - timedelta(days=1),
    )

    url = "/"
    response = client.get(url)

    assert "First news" not in response.content.decode()
    assert "Second news" in response.content.decode()
    assert "Third news content" in response.content.decode()
    assert "Fourth news" in response.content.decode()


def test_homepage_doesnt_display_news_from_non_current_conference(db, client):
    current_code = settings.CONFERENCE_CONFERENCE
    current_conf = ConferenceFactory(code=current_code)
    other_conf = ConferenceFactory(code="other")

    News.objects.create(
        conference=current_conf,
        title="Current news",
        content="Current news content",
        status=News.STATUS.PUBLISHED,
        published_date=timezone.now() - timedelta(days=2),
    )
    News.objects.create(
        conference=other_conf,
        title="Old news",
        content="Old news content",
        status=News.STATUS.PUBLISHED,
        published_date=timezone.now() - timedelta(days=365),
    )

    url = "/"
    response = client.get(url)

    assert "Current news" in response.content.decode()
    assert "Old news" not in response.content.decode()


@pytest.mark.xfail
def test_homepage_news_supports_html_tags(db, client):
    assert False


def test_homepage_doesnt_contain_sponsor_if_no_income(db, client):
    sponsor = SponsorFactory(
        alt_text="Sponsor Alt Text", title_text="Sponsor Title Text"
    )

    url = "/"
    response = client.get(url)

    assert sponsor.alt_text not in response.content.decode()
    assert sponsor.title_text not in response.content.decode()


def test_homepage_doesnt_contain_sponsor_if_income_for_different_conference(
    db, client
):

    sponsor = SponsorFactory(
        alt_text="Sponsor Alt Text", title_text="Sponsor Title Text"
    )
    sponsor.sponsorincome_set.create(income=123, conference="whatever2020")

    url = "/"
    response = client.get(url)

    assert sponsor.alt_text not in response.content.decode()
    assert sponsor.title_text not in response.content.decode()


def test_homepage_contains_sponsors_if_income_for_current_conference(
    db, client
):
    sponsor = SponsorFactory(
        alt_text="Sponsor Alt Text", title_text="Sponsor Title Text"
    )
    sponsor.sponsorincome_set.create(
        income=123, conference=settings.CONFERENCE_CONFERENCE
    )
    url = "/"
    response = client.get(url)

    assert sponsor.alt_text in response.content.decode()
    assert sponsor.title_text in response.content.decode()


def test_homepage_contains_googleanalytics(db, client):
    url = "/"
    response = client.get(url)
    assert response.status_code == 200

    EPCON_2019_GA_ID = "UA-60323107-5"
    # NOTE(artcz) this should probably go into a variable, but good enough for
    assert EPCON_2019_GA_ID in response.content.decode()
