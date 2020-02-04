import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save

from assopy.models import ticket_for_user, user_created
from assopy import dataaccess as cd
from conference.listeners import fare_tickets
from conference.models import AttendeeProfile, Ticket

from . import models

log = logging.getLogger('p3')


def on_ticket_for_user(sender, **kwargs):
    from p3 import dataaccess
    tickets = dataaccess.user_tickets(sender.user, settings.CONFERENCE_CONFERENCE, only_complete=True)
    list(map(kwargs['tickets'].append, tickets))


ticket_for_user.connect(on_ticket_for_user)


def on_profile_created(sender, **kw):
    if kw['created']:
        models.P3Profile(profile=kw['instance']).save()


post_save.connect(on_profile_created, sender=AttendeeProfile)


def on_user_created(sender, **kw):
    if kw['profile_complete']:
        # The user has been created using email+password form, I won't get other data
        AttendeeProfile.objects.getOrCreateForUser(sender.user)
    else:
        # The user has been created, I don't create the profile now
        # waiting for the first identity
        pass


user_created.connect(on_user_created)


def create_p3_auto_assigned_conference_tickets(sender, params=None, **kws):
    # print ('create_p3_conference_tickets: %r %r %r' % (sender, params, kws))
    fare = sender

    # Only create conference tickets with this helper
    if fare.ticket_type != 'conference':
        return

    # Get parameters sent by Fare.create_tickets()
    if params is None:
        return

    created_tickets = params['tickets']
    user = params['user']

    # Tickets may have not yet been created, so do this now. This
    # overrides the default ticket in Fare.created_tickets(), but
    # allows us to apply the auto-assign below, even for the first
    # ticket
    if not created_tickets:
        ticket = Ticket(user=user, fare=fare)
        ticket.fare_description = fare.name
        ticket.save()
        created_tickets.append(ticket)

    # Create P3 TicketConference records and assign them to the user,
    # if not already done
    from p3 import utils
    for ticket in created_tickets:
        utils.assign_ticket_to_user(ticket, user)


fare_tickets.connect(create_p3_auto_assigned_conference_tickets)


# redefining user_tickets of assopy to include assined tickets
_original = cd.user_tickets


def _user_tickets(u):
    data = _original(u)
    # adding to already selected tickets the email of the person to who
    # they've been assigned to
    from p3.models import TicketConference

    tids = [x['id'] for x in data]
    tickets = (
        TicketConference.objects
            .filter(ticket__in=tids)
            .exclude(assigned_to="")
            .values('ticket', 'assigned_to')
    )
    info = dict([(x['ticket'], x['assigned_to']) for x in tickets])

    for x in data:
        try:
            x['note'] = 'to: %s' % info[x['id']]
        except KeyError:
            continue

    # adding tickets assigned to the user
    qs = (
        Ticket.objects
            .filter(p3_conference__assigned_to__iexact=u.email)
            .order_by('-fare__conference')
            .select_related('fare')
    )

    from assopy.models import Order

    def order(t):
        try:
            o = Order.objects.get(orderitem__ticket=t)
        except models.Order.DoesNotExist:
            return {}
        return {
            'code': o.code,
            'created': o.created,
            'url': reverse('admin:assopy_order_change', args=(o.id,)),
        }

    for t in qs:
        data.append({
            'id': t.id,
            'type': t.ticket_type,
            'fare': {
                'code': t.fare.code,
                'conference': t.fare.conference,
                'recipient': t.fare.recipient_type,
            },
            'note': 'from: %s %s' % (t.user.first_name, t.user.last_name),
            'order': order(t),
        })
    return data


cd.user_tickets = _user_tickets  # noqa
