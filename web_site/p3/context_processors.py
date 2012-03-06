# -*- coding: UTF-8 -*-
def countdown(request):
    from assopy.models import OrderItem
    from django.conf import settings
    from django.db.models import Count

    sold = OrderItem.objects.filter(order___complete=True)\
            .filter(ticket__fare__conference=settings.CONFERENCE_CONFERENCE)\
            .values('ticket__fare__code')\
            .annotate(c=Count('pk'))

    conference = 679 - sum(
        x['c'] for x in sold.filter(ticket__fare__ticket_type='conference')
    )
    pyfiorentina = 220 - sum(
        x['c'] for x in sold.filter(ticket__fare__code='VOUPE02')
    )
    return {
        'COUNTDOWN': {
            'conference': conference,
            'pyfiorentina': pyfiorentina,
        },
    }

