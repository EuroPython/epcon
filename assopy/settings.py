# -*- coding: UTF-8 -*-
from django.conf import settings

if hasattr(settings, 'ASSOPY_JANRAIN'):
    JANRAIN = {
        'domain': settings.ASSOPY_JANRAIN['domain'],
        'app_id': settings.ASSOPY_JANRAIN['app_id'],
        'secret': settings.ASSOPY_JANRAIN['secret'],
    }
else:
    JANRAIN = None

try:
    BACKEND = settings.ASSOPY_BACKEND
except AttributeError:
    BACKEND = None

CHECK_DB_SCHEMA = getattr(settings, 'ASSOPY_CHECK_DB_SCHEMA', True)

SEARCH_MISSING_USERS_ON_BACKEND = getattr(settings, 'ASSOPY_SEARCH_MISSING_USERS_ON_BACKEND', False)

TICKET_PAGE = getattr(settings, 'ASSOPY_TICKET_PAGE', None)

SEND_EMAIL_TO = getattr(settings, 'ASSOPY_SEND_EMAIL_TO', None)

REFUND_EMAIL_ADDRESS = getattr(settings, 'ASSOPY_REFUND_EMAIL_ADDRESS', {
    'approve': SEND_EMAIL_TO,
    'execute': {None: SEND_EMAIL_TO},
    'credit-note': SEND_EMAIL_TO,
})

VIES_WSDL_URL = getattr(settings, 'ASSOPY_VIES_WSDL_URL', 'http://ec.europa.eu/taxation_customs/vies/checkVatService.wsdl')

OTC_CODE_HANDLERS = {
    'v': 'assopy.views.OTCHandler_V',
    'j': 'assopy.views.OTCHandler_J',
}
OTC_CODE_HANDLERS.update(getattr(settings, 'ASSOPY_OTC_CODE_HANDLERS', {}))

def _ASSOPY_NEXT_ORDER_CODE(order):
    """
    Ritorna un codice di ordine nel formato specificato
    """
    import datetime
    import models
    try:
        last_code = models.Order.objects \
                      .filter(code__startswith='O/%s.' % str(datetime.date.today().year)[2:]) \
                      .order_by('-code') \
                      .values_list('code',flat=True)[0]
        last_number = int(last_code[5:])
    except IndexError:
        last_number = 0

    return "O/%s.%s" % (str(datetime.date.today().year)[2:], str(last_number + 1).zfill(4))

NEXT_ORDER_CODE = getattr(settings, 'ASSOPY_NEXT_ORDER_CODE', _ASSOPY_NEXT_ORDER_CODE)

def _ASSOPY_NEXT_CREDIT_CODE(credit_note):
    """
    Ritorna Il prossimo codice per una nota di credito
    """
    import datetime
    import models
    try:
        last_code = models.CreditNote.objects \
                      .filter(code__startswith='C/%s.' % str(datetime.date.today().year)[2:]) \
                      .order_by('-code') \
                      .values_list('code',flat=True)[0]
        last_number = int(last_code[5:])
    except IndexError:
        last_number = 0

    return "C/%s.%s" % (str(datetime.date.today().year)[2:], str(last_number + 1).zfill(4))

NEXT_CREDIT_CODE = getattr(settings, 'ASSOPY_NEXT_CREDIT_CODE', _ASSOPY_NEXT_CREDIT_CODE)

if 'paypal.standard.ipn' in settings.INSTALLED_APPS:
    def _PAYPAL_DEFAULT_FORM_CONTEXT(order):
        from django.core.urlresolvers import reverse
        code = order.code.replace('/','-')
        return {
            "lc" : settings.LANGUAGE_CODE.upper(),
            "custom": order.code,
            "currency_code" : 'EUR',
            "business": settings.PAYPAL_RECEIVER_EMAIL,
            "notify_url": "%s%s" % (settings.DEFAULT_URL_PREFIX, reverse('paypal-ipn')),
            "return_url": "%s%s" % (settings.DEFAULT_URL_PREFIX, reverse('assopy-paypal-feedback-ok', kwargs={'code':code})),
            "cancel_return": "%s%s" % (settings.DEFAULT_URL_PREFIX, reverse('assopy-paypal-feedback-cancel', kwargs={'code':code})),
        }

    PAYPAL_DEFAULT_FORM_CONTEXT = getattr(settings, 'PAYPAL_DEFAULT_FORM_CONTEXT', _PAYPAL_DEFAULT_FORM_CONTEXT)

    def _PAYPAL_ITEM_NAME(item):
        return "%s %s" % (item['code'], item['description'])

    PAYPAL_ITEM_NAME = getattr(settings, 'PAYPAL_ITEM_NAME', _PAYPAL_ITEM_NAME)

#WKHTMLTOPDF_PATH = getattr(settings,'ASSOPY_WKHTMLTOPDF_PATH', None)
WKHTMLTOPDF_PATH = '/usr/bin/wkhtmltopdf'


def _ORDERITEM_CAN_BE_REFUNDED(user, item):
    return False

ORDERITEM_CAN_BE_REFUNDED = getattr(settings, 'ASSOPY_ORDERITEM_CAN_BE_REFUNDED', _ORDERITEM_CAN_BE_REFUNDED)
