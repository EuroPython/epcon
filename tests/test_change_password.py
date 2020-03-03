from datetime import date
from pytest import mark

from django.urls import reverse
from django.conf import settings

from conference.models import AttendeeProfile, Conference

from .common_tools import template_used
from . import factories


@mark.django_db
def test_change_password(client, user):
    """
    Testing full change password flow,

    1. Log in
    2. Look for change password url on the profile page
    3. Change the password.
    4. Log in with new password
    """

    # Conference is needed for user panel to work properly – because of
    # proposals and orders
    Conference.objects.create(
        code=settings.CONFERENCE_CONFERENCE,
        name=settings.CONFERENCE_CONFERENCE,
        conference_start=date.today(),
    )

    client.login(email=user.email, password="password123")

    user_dashboard_url = reverse("user_panel:dashboard")
    change_password_url = reverse("user_panel:password_change")

    response = client.get(user_dashboard_url)
    assert "Change your password" in response.content.decode("utf-8")
    assert change_password_url in response.content.decode("utf-8")
    assert template_used(response, "conference/user_panel/dashboard.html")

    response = client.get(change_password_url)
    assert template_used(
        response, "conference/user_panel/password_change.html"
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
        response, "conference/user_panel/password_change_done.html"
    )
    assert user_dashboard_url in response.content.decode("utf-8")
    assert "Password updated" in response.content.decode("utf-8")

    client.logout()

    can_log_in_with_new_password = client.login(email=user.email, password="pwd345")
    assert can_log_in_with_new_password
