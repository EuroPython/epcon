# -*- coding: UTF-8 -*-

from assopy import settings
from suds.client import Client

_client = Client(settings.VIES_WSDL_URL)

def check_vat(country, vat):
    return c.service.checkVat(country, vat)['valid']
