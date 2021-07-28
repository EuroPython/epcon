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
    assert b"EuroPython 2021" in response.content


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
    sponsor.sponsorincome_set.create(income=123, conference="whatever2021")

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


def test_homepage_contains_sponsors_sorted_by_income(db, client):
    create_homepage_in_cms()
    a_sponsor = SponsorFactory(
        alt_text="A Sponsor Alt Text", title_text="A Sponsor Title Text"
    )
    b_sponsor = SponsorFactory(
        alt_text="B Sponsor Alt Text", title_text="B Sponsor Title Text"
    )
    c_sponsor = SponsorFactory(
        alt_text="C Sponsor Alt Text", title_text="B Sponsor Title Text"
    )

    a_sponsor.sponsorincome_set.create(
        income=123, conference=settings.CONFERENCE_CONFERENCE
    )
    b_sponsor.sponsorincome_set.create(
        income=789, conference=settings.CONFERENCE_CONFERENCE
    )
    c_sponsor.sponsorincome_set.create(
        income=456, conference=settings.CONFERENCE_CONFERENCE
    )
    url = "/"
    response = client.get(url)

    a_sponsor_position = response.content.decode().find('A Sponsor')
    b_sponsor_position = response.content.decode().find('B Sponsor')
    c_sponsor_position = response.content.decode().find('C Sponsor')

    assert b_sponsor_position < c_sponsor_position < a_sponsor_position


def test_homepage_contains_googleanalytics(db, client):
    create_homepage_in_cms()
    url = "/"
    response = client.get(url)
    assert response.status_code == 200

    assert 'https://www.googletagmanager.com/gtag/js' in response.content.decode()
