from datetime import date
from pytest import mark

from django.core.urlresolvers import reverse
from django.conf import settings

from django_factory_boy import auth as auth_factories

from conference.models import AttendeeProfile, Conference

from tests.common_tools import template_used
from tests.factories import AssopyUserFactory


@mark.django_db
def test_change_password(client):
    """
    Testing full change password flow,

    1. Log in
    2. Look for change password url on the profile page
    3. Change the password.
    4. Log in with new password
    """

    # default password is 'password123' per django_factory_boy
    user = auth_factories.UserFactory(
        email="joedoe@example.com", is_active=True
    )
    # Conference is needed for user panel to work properly – because of
    # proposals and orders
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        conference_start=date.today(),
    )

    # both are required to access user profile page.
    AssopyUserFactory(user=user)
    AttendeeProfile.objects.create(user=user, slug="foobar")

    client.login(email="joedoe@example.com", password="password123")

    user_dashboard_url = reverse("user_panel:dashboard")
    change_password_url = reverse("user_panel:password_change")

    response = client.get(user_dashboard_url)
    assert "Change your password" in response.content.decode("utf-8")
    assert change_password_url in response.content.decode("utf-8")
    assert template_used(response, "ep19/bs/user_panel/dashboard.html")

    response = client.get(change_password_url)
    assert template_used(
        response, "ep19/bs/user_panel/password_change.html"
    )
    assert "Django Administration" not in response.content.decode("utf-8")

    response = client.post(
        change_password_url,
        {
            "old_password": "password123",
            "new_password1": "pwd345",
            "new_password2": "pwd345",
        },
        follow=True,
    )

    assert template_used(
        response, "ep19/bs/user_panel/password_change_done.html"
    )
    assert user_dashboard_url in response.content.decode("utf-8")
    assert "Password updated" in response.content.decode("utf-8")

    client.logout()

    can_log_in_with_new_password = client.login(
        email="joedoe@example.com", password="pwd345"
    )
    assert can_log_in_with_new_password
