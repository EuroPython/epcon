import pytest

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from tests.common_tools import template_used
from tests.factories import ConferenceFactory, SponsorFactory, NewsFactory
from tests.common_tools import get_default_conference


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
    get_default_conference()

    first_news = NewsFactory(
        title="First news",
        published_date=timezone.now() - timedelta(days=4),
    )
    second_news = NewsFactory(
        title="Second news",
        published_date=timezone.now() - timedelta(days=3),
    )
    third_news = NewsFactory(
        title="Third news",
        published_date=timezone.now() - timedelta(days=2),
    )
    fourth_news = NewsFactory(
        title="Fourth news",
        published_date=timezone.now() - timedelta(days=1),
    )

    url = "/"
    response = client.get(url)

    assert first_news.title not in response.content.decode()
    assert second_news.title in response.content.decode()
    assert third_news.content in response.content.decode()
    assert fourth_news.title in response.content.decode()


def test_homepage_doesnt_display_news_from_non_current_conference(db, client):
    current_conf = get_default_conference()
    other_conf = ConferenceFactory(code="other", name="other conf")

    current_news = NewsFactory(
        conference=current_conf,
        published_date=timezone.now() - timedelta(days=2),
    )
    old_news = NewsFactory(
        conference=other_conf,
        published_date=timezone.now() - timedelta(days=365),
    )

    url = "/"
    response = client.get(url)

    assert current_news.title in response.content.decode()
    assert old_news.title not in response.content.decode()


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
