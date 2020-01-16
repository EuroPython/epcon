import pytest

from django.core.urlresolvers import reverse

from conference.models import ATTENDEEPROFILE_VISIBILITY, TALK_STATUS

from tests.common_tools import make_user, create_talk_for_user, template_used, get_default_conference
from tests.factories import TicketFactory

pytestmark = [pytest.mark.django_db]


def test_profile_page_available_during_voting_with_proposal(client):
    get_default_conference()
    profile_user = make_user()
    create_talk_for_user(profile_user)
    url = reverse("profiles:profile", kwargs={"profile_slug": profile_user.attendeeprofile.slug})

    # Profile unavailable for unauthenticated users.
    response = client.get(url)
    assert template_used(response, "ep19/bs/profiles/profile_unavailable.html")

    # Profile unavailable for authenticated users that are no legible to vote (never bought tickets).
    request_user = make_user()
    client.force_login(request_user)
    response = client.get(url)
    assert template_used(response, "ep19/bs/profiles/profile_unavailable.html")

    # Requesting user needs to be eligible to vote, i.e. have bought a ticket for any of the conferences
    TicketFactory(user=request_user)
    response = client.get(url)
    assert template_used(response, "ep19/bs/profiles/profile.html")


def test_profile_page_available_if_public(client):
    get_default_conference()
    profile_user = make_user()
    profile_user.attendeeprofile.visibility = ATTENDEEPROFILE_VISIBILITY.PUBLIC
    profile_user.attendeeprofile.save()
    url = reverse("profiles:profile", kwargs={"profile_slug": profile_user.attendeeprofile.slug})

    # Profile available for unauthenticated users.
    response = client.get(url)
    assert template_used(response, "ep19/bs/profiles/profile.html")

    # Profile available for authenticated users.
    request_user = make_user()
    client.force_login(request_user)
    response = client.get(url)
    assert template_used(response, "ep19/bs/profiles/profile.html")


def test_profile_page_available_if_participant_only_and_authenticated(client):
    get_default_conference()
    profile_user = make_user()
    profile_user.attendeeprofile.visibility = ATTENDEEPROFILE_VISIBILITY.PARTICIPANTS_ONLY
    profile_user.attendeeprofile.save()
    url = reverse("profiles:profile", kwargs={"profile_slug": profile_user.attendeeprofile.slug})

    # Profile unavailable for unauthenticated users.
    response = client.get(url)
    assert template_used(response, "ep19/bs/profiles/profile_unavailable.html")

    # Profile available for authenticated users.
    request_user = make_user()
    client.force_login(request_user)
    response = client.get(url)
    assert template_used(response, "ep19/bs/profiles/profile.html")


def test_profile_page_available_if_has_accepted_talks(client):
    get_default_conference()
    profile_user = make_user()
    talk = create_talk_for_user(profile_user)
    talk.status = TALK_STATUS.accepted
    talk.save()
    url = reverse("profiles:profile", kwargs={"profile_slug": profile_user.attendeeprofile.slug})

    # Profile unavailable for unauthenticated users.
    response = client.get(url)
    assert template_used(response, "ep19/bs/profiles/profile.html")

    # Profile unavailable for authenticated users that are no legible to vote (never bought tickets).
    request_user = make_user()
    client.force_login(request_user)
    response = client.get(url)
    assert template_used(response, "ep19/bs/profiles/profile.html")


def test_profile_page_fields_empty_profile(client):
    """
    If no additional information is published on the profile page, it will
    render at least the following fields with blanks:
    location, company, job title, company website
    """
    get_default_conference()
    profile_user = make_user()
    profile_user.attendeeprofile.visibility = ATTENDEEPROFILE_VISIBILITY.PUBLIC
    profile_user.attendeeprofile.save()
    url = reverse("profiles:profile", kwargs={"profile_slug": profile_user.attendeeprofile.slug})

    response = client.get(url)

    assert template_used(response, "ep19/bs/profiles/profile.html")
    assert 'id="biography"' in response.content.decode().lower()
    assert 'id="company"' in response.content.decode().lower()
    assert 'id="job-title"' in response.content.decode().lower()
    assert 'id="company-website"' in response.content.decode().lower()

    assert 'id="location"' not in response.content.decode().lower()
    assert 'id="tagline"' not in response.content.decode().lower()
    assert 'id="personal-website"' not in response.content.decode().lower()
    assert 'id="twitter"' not in response.content.decode().lower()


def test_profile_page_fields(client):
    """
    If available, those fields will also be rendered on the page:
    tagline, website, twitter, location
    """
    get_default_conference()
    profile_user = make_user()
    profile_user.attendeeprofile.visibility = ATTENDEEPROFILE_VISIBILITY.PUBLIC
    profile_user.attendeeprofile.personal_homepage = 'website'
    profile_user.attendeeprofile.location = 'location'
    profile_user.attendeeprofile.save()
    profile_user.attendeeprofile.p3_profile.twitter = 'twitter'
    profile_user.attendeeprofile.p3_profile.tagline = 'tagline'
    profile_user.attendeeprofile.p3_profile.save()
    url = reverse("profiles:profile", kwargs={"profile_slug": profile_user.attendeeprofile.slug})

    response = client.get(url)

    assert template_used(response, "ep19/bs/profiles/profile.html")
    assert 'id="biography"' in response.content.decode().lower()
    assert 'id="company"' in response.content.decode().lower()
    assert 'id="job-title"' in response.content.decode().lower()
    assert 'id="company-website"' in response.content.decode().lower()
    assert 'id="location"' in response.content.decode().lower()
    assert 'id="tagline"' in response.content.decode().lower()
    assert 'id="personal-website"' in response.content.decode().lower()
    assert 'id="twitter"' in response.content.decode().lower()
