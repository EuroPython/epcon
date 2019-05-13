import pytest

pytestmark = [pytest.mark.django_db]


@pytest.mark.xfail
def test_talk_voting_unavailable_if_not_enabled():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_unavailable_without_a_ticket():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_available_with_ticket_and_enabled():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_filters():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_hides_admin_talks():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_hides_approved_talks():
    assert True == False


@pytest.mark.xfail
def test_talk_voting_creates_new_vote():
    assert True == False
