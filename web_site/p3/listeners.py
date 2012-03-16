# -*- coding: UTF-8 -*-
import logging
import models

from assopy.models import order_created, purchase_completed, ticket_for_user, user_created, user_identity_created
from conference.listeners import fare_price, fare_tickets
from conference.models import AttendeeProfile, Ticket
from django.conf import settings
from django.db.models.signals import post_save
from email_template import utils

log = logging.getLogger('p3')

def on_order_created(sender, **kwargs):
    if sender.total() == 0:
        on_purchase_completed(sender)
    elif sender.method == 'bank':
        utils.email(
            'bank-order-complete',
            ctx={'order': sender,},
            to=[sender.user.user.email]
        ).send()

    ritems = kwargs['raw_items']
    for fare, params in ritems:
        # se l'ordine contiene delle prenotazione alberghiere devo creare i
        # relativi ticket adesso, perchè le informazioni sul periodo le ho solo
        # tramite ritems
        if fare.code[0] == 'H':
            log.info('The newly created order "%s" includes %d hotel reservations "%s" for the period: "%s" -> "%s".', sender.code, params['qty'], fare.code, params['period'][0], params['period'][1])
            loop = params['qty']
            if fare.code[1] == 'R':
                loop *= int(fare.code[2])
            for _ in range(loop):
                t = Ticket.objects.filter(fare=fare, user=sender.user.user, p3_conference_room=None)[0]
                room = models.TicketRoom(ticket=t)
                room.ticket_type = fare.code[1]
                room.room_type = models.HotelRoom.objects.get(conference=fare.conference, room_type='t%s' % fare.code[2])
                room.checkin = params['period'][0]
                room.checkout = params['period'][1]
                room.save()

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
    from p3 import dataaccess
    tickets = dataaccess.user_tickets(sender.user, settings.CONFERENCE_CONFERENCE, only_complete=True)
    map(kwargs['tickets'].append, tickets)

ticket_for_user.connect(on_ticket_for_user)


def on_profile_created(sender, **kw):
    if kw['created']:
        models.P3Profile(profile=kw['instance']).save()

post_save.connect(on_profile_created, sender=AttendeeProfile)

def on_user_created(sender, **kw):
    if kw['profile_complete']:
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
    room = models.HotelRoom.objects.get(conference=sender.conference, room_type='t' + sender.code[2])
    price = room.price(days=(period[1] - period[0]).days)
    if sender.code[1] == 'R':
        price *= int(sender.code[2])
    calc['total'] = price * calc['params']['qty']
fare_price.connect(calculate_hotel_reservation_price)

def create_hotel_tickets(sender, **kw):
    # solo per le prenotazioni di intere camere devo creare più biglietti, per
    # tutti gli altri casi mi va bene il comportamento standard
    if sender.code[:2] == 'HR':
        for _ in range(int(sender.code[2])):
            t = Ticket(user=kw['params']['user'], fare=sender)
            t.save()
            kw['params']['tickets'].append(t)

fare_tickets.connect(create_hotel_tickets)
