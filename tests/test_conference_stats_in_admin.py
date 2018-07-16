# coding: utf-8

from __future__ import unicode_literals, absolute_import, print_function

from pytest import mark

from tests.common_tools import make_user

URL = "/admin/conference/conference/ep2018/stats/"
HTTP_OK_200 = 200
HTTP_LOGIN_REQUIRED_REDIRECT_302 = 302


@mark.django_db
def test_if_stats_are_not_accessible_to_regular_users(client):
    """
    Mainly tests if we don't get a random 500 due to an obvious bug in a lower
    level code.
    """
    make_user(is_staff=False)
    client.login(email='joedoe@example.com', password='joedoe')
    response = client.get(URL)
    assert response.status_code == HTTP_LOGIN_REQUIRED_REDIRECT_302


@mark.django_db
def test_if_stats_are_accessible_in_admin(admin_client):
    """
    Mainly tests if we don't get a random 500 due to an obvious bug in a lower
    level code.
    """
    response = admin_client.get(URL)
    assert response.status_code == HTTP_OK_200
