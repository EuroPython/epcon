import pytest

pytestmark = [pytest.mark.django_db]


@pytest.mark.xfail
def test_privacy_settings_requires_login():
    assert False


@pytest.mark.xfail
def test_privacy_settings_updates_profile():
    assert False
