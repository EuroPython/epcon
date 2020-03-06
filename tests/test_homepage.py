from django.conf import settings

from tests.common_tools import template_used
from tests.factories import SponsorFactory
from tests.common_tools import create_homepage_in_cms


def test_get_homepage(db, client):
    create_homepage_in_cms()
    url = "/"
    response = client.get(url)

    assert response.status_code == 200
    assert template_used(response, "conference/homepage/home_template.html")
    assert template_used(response, "conference/homepage/_venue.html")
    assert template_used(response, "conference/homepage/_sponsors.html")
    assert template_used(response, "conference/homepage/_schedule_overview.html")
    assert template_used(response, "conference/header/_with_jumbotron.html")
    assert b"EuroPython 2020" in response.content


def test_homepage_doesnt_contain_sponsor_if_no_income(db, client):
    create_homepage_in_cms()
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
    create_homepage_in_cms()

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
    create_homepage_in_cms()
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
    create_homepage_in_cms()
    url = "/"
    response = client.get(url)
    assert response.status_code == 200

    EPCON_GA_ID = "UA-60323107"
    # NOTE(artcz) this should probably go into a variable, but good enough for
    assert EPCON_GA_ID in response.content.decode()
