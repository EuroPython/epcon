# coding: utf-8

from __future__ import unicode_literals, absolute_import, print_function

from pytest import mark


@mark.django_db
def test_if_stats_are_accessible_in_admin(admin_client):
    """
    Mainly tests if we don't get a random 500 due to an obvious bug in a lower
    level code.
    """
    url = "/admin/conference/conference/ep2018/stats/"
    HTTP_OK_200 = 200

    response = admin_client.get(url)
    assert response.status_code == HTTP_OK_200
