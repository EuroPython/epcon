# -*- coding: UTF-8 -*-
from assopy import settings
from suds.client import Client

if settings.VIES_WSDL_URL:
    _client = Client(settings.VIES_WSDL_URL)
else:
    _client = None

def check_vat(country, vat):
    return _client.service.checkVat(country, vat)['valid']
