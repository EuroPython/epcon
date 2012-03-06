# -*- coding: UTF-8 -*-
import models

from assopy.models import order_created, purchase_completed, ticket_for_user, user_created, user_identity_created
from conference.listeners import fare_price
from conference.models import AttendeeProfile
from django.conf import settings
from django.db.models.signals import post_save
from email_template import utils

def on_order_created(sender, **kwargs):
    if sender.total() == 0:
        on_purchase_completed(sender)
    elif sender.method == 'bank':
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


def on_profile_created(sender, **kw):
    if kw['created']:
        models.P3Profile(profile=kw['instance']).save()

post_save.connect(on_profile_created, sender=AttendeeProfile)

def on_user_created(sender, **kw):
    if kw['password_set']:
        # L'utente è stato creato utilizzando la form email+password, non avrò
        # altri dati
        AttendeeProfile.objects.getOrCreateForUser(sender.user)
    else:
        # L'utente ha utilizzato janrain, non creo il profilo ora ma aspetto la
        # prima identità
        pass

user_created.connect(on_user_created)

def on_user_identity_created(sender, **kw):
    identity = kw['identity']
    profile = AttendeeProfile.objects.getOrCreateForUser(sender.user)
    if identity.user.identities.count() > 1:
        # non è la prima identità non copio niente per non sovrascrivere
        # i dati cambiati dall'utente
        return

user_identity_created.connect(on_user_identity_created)

def calculate_hotel_reservation_price(sender, **kw):
    if sender.code[0] != 'H':
        return
    # il costo di una prenotazione alberghiera varia in funzione del periodo
    calc = kw['calc']
    period = calc['params']['period']
    qty = calc['params']['qty']
    calc['total'] = 5 * qty
fare_price.connect(calculate_hotel_reservation_price)
