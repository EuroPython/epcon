import pytest


pytestmark = [pytest.mark.django_db]


@pytest.mark.xfail
def test_speaker_page_available_during_voting_with_proposal():
    assert False


@pytest.mark.xfail
def test_speaker_page_available_if_public():
    assert False


@pytest.mark.xfail
def test_speaker_page_available_if_participant_only_and_authenticated():
    assert False


@pytest.mark.xfail
def test_speaker_page_available_if_has_accepted_talks():
    assert False


@pytest.mark.xfail
def test_speaker_page_unavailable_template():
    assert False


@pytest.mark.xfail
def test_speaker_page_fields_empty_profile():
    """
    If no additional information is published on the speaker page, it will
    render at least the following fields with blanks:
    location, company, job title, company website
    """
    assert False


@pytest.mark.xfail
def test_speaker_page_fields():
    """
    If available, those fields will also be rendered on the page:
    tagline, website, twitter, location
    """
    assert False
