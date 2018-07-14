# coding: utf-8


def test_index(admin_client):
    """
    Basic test to see if it even works.
    """
    url = "/nothing-to-see-here/"
    HTTP_OK_200 = 200

    respnse = admin_client.get(url)
    assert respnse.status_code == HTTP_OK_200
