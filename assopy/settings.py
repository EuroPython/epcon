
from django.conf import settings

try:
    BACKEND = settings.ASSOPY_BACKEND
except AttributeError:
    BACKEND = None

SEARCH_MISSING_USERS_ON_BACKEND = getattr(settings, 'ASSOPY_SEARCH_MISSING_USERS_ON_BACKEND', False)

SEND_EMAIL_TO = getattr(settings, 'ASSOPY_SEND_EMAIL_TO', None)

REFUND_EMAIL_ADDRESS = getattr(settings, 'ASSOPY_REFUND_EMAIL_ADDRESS', {
    'approve': SEND_EMAIL_TO,
    'execute': {None: SEND_EMAIL_TO},
    'credit-note': SEND_EMAIL_TO,
})



def _ASSOPY_NEXT_CREDIT_CODE(credit_note):
    """
    Ritorna Il prossimo codice per una nota di credito
    """
    import datetime
    from . import models
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


#WKHTMLTOPDF_PATH = getattr(settings,'ASSOPY_WKHTMLTOPDF_PATH', None)
WKHTMLTOPDF_PATH = '/usr/bin/wkhtmltopdf'
