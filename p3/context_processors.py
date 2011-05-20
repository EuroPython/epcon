# -*- coding: UTF-8 -*-
#from datetime import date
#from conference import assopy
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

def static(request):
    return { 'STATIC_URL': settings.STATIC_URL }

def countdown(request):
    from assopy.models import OrderItem
    from django.db.models import Count
    qs = OrderItem.objects.filter(order___complete=True)
    conference = 600 - sum(x['c'] for x in qs.values('ticket__fare__code')\
                                        .filter(ticket__fare__ticket_type='conference')\
                                        .annotate(c=Count('pk')))
    pyfiorentina = 220 - sum(x['c'] for x in qs.values('ticket__fare__code')\
                                        .filter(ticket__fare__code='VOUPE02')\
                                        .annotate(c=Count('pk')))
    return {
        'COUNTDOWN': {
            'conference': conference,
            'pyfiorentina': pyfiorentina,
        },
    }

