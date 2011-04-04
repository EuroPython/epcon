# -*- coding: UTF-8 -*-
import models

from django.conf import settings
from email_template import utils
from assopy.models import order_created, purchase_completed, ticket_for_user

def on_order_created(sender, **kwargs):
    if sender.method == 'bank':
        utils.email(
            'bank-order-complete',
            ctx={'order': sender,},
            to=[sender.user.user.email]
        ).send()

order_created.connect(on_order_created)

def on_purchase_completed(sender, **kwargs):
    if sender.method == 'admin':
        return
    utils.email(
        'purchase-complete',
        ctx={
            'order': sender,
            'student': sender.orderitem_set.filter(ticket__fare__recipient_type='s').count() > 0,
        },
        to=[sender.user.user.email],
    ).send()

purchase_completed.connect(on_purchase_completed)

def on_ticket_for_user(sender, **kwargs):
    tickets = models.TicketConference.objects.available(sender.user, settings.CONFERENCE_CONFERENCE)
    map(kwargs['tickets'].append, tickets)

ticket_for_user.connect(on_ticket_for_user)
