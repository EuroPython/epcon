# -*- coding: UTF-8 -*-
def countdown(request):
    from assopy.models import OrderItem
    from django.db.models import Count
    qs = OrderItem.objects.filter(order___complete=True)
    conference = 679 - sum(x['c'] for x in qs.values('ticket__fare__code')\
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

