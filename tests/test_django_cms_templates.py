# coding: utf-8

from __future__ import unicode_literals, absolute_import

from pytest import mark

from tests.common_tools import template_used  # , template_paths


# needs to be marked because Django CMS will interfere
@mark.django_db
def test_if_menu_html_template_is_used_on_404_page(client):
    url = "/asasd/foo/bar/404/"
    response = client.get(url, follow=True)
    assert template_used(response, '404.html', http_status=404)
    assert template_used(response, 'menu/menu.html', http_status=404)
