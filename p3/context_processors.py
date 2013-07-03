# -*- coding: UTF-8 -*-
from django.core.cache import cache

def countdown(request):
    from assopy.models import OrderItem
    from django.conf import settings
    from django.db.models import Count, Q

    sold = OrderItem.objects.filter(Q(order___complete=True) | Q(order__method__in=('bank', 'admin')))\
            .filter(ticket__fare__conference=settings.CONFERENCE_CONFERENCE)\
            .values('ticket__fare__code')\
            .annotate(c=Count('pk'))

    conference = cache.get('p3_countdown_conference')
    if conference is None:
        conference = 750 - sum(
            x['c'] for x in sold.filter(ticket__fare__ticket_type='conference')
        )
        if conference > 10:
            cache.set('p3_countdown_conference', conference, 60)
    pyfiorentina = cache.get('p3_countdown_pyfiorentina')
    if pyfiorentina is None:
        pyfiorentina = 360 - sum(
            x['c'] for x in sold.filter(ticket__fare__code='VOUPE03')
        )
        if pyfiorentina > 10:
            cache.set('p3_countdown_pyfiorentina', pyfiorentina, 60)
    return {
        'COUNTDOWN': {
            'conference': conference,
            'pyfiorentina': pyfiorentina,
        },
    }

