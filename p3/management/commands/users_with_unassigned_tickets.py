# -*- coding: utf-8 -*-
""" Print information of the users who got unassigned tickets."""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from p3 import models as p3_models
from assopy import models as assopy_models

from optparse import make_option

### Globals

### Helpers

def conference_year(conference=settings.CONFERENCE_CONFERENCE):
    return conference[-2:]


def get_all_order_tickets(conference=settings.CONFERENCE_CONFERENCE):

    year = conference_year(conference)

    orders          = assopy_models.Order.objects.filter(_complete=True)
    conf_orders     = [order for order in orders if order.code.startswith('O/{}.'.format(year))]
    order_tkts      = [ordi.ticket
                       for order in conf_orders
                       for ordi in order.orderitem_set.all()
                       if ordi.ticket is not None]
    conf_order_tkts = [ot for ot in order_tkts if ot.fare.code.startswith('T')]

    return conf_order_tkts


def get_assigned_ticket(ticket_id):
    return p3_models.TicketConference.objects.filter(ticket=ticket_id)


def has_assigned_ticket(ticket_id):
    return bool(get_assigned_ticket(ticket_id))

# def is_ticket_assigned_to_someone_else(ticket, user):
#     tickets = p3_models.TicketConference.objects.filter(ticket_id=ticket.id)
#
#     if not tickets:
#         return False
#         #from IPython.core.debugger import Tracer
#         #Tracer()()
#         #raise RuntimeError('Could not find any ticket with ticket_id {}.'.format(ticket))
#
#     if len(tickets) > 1:
#         raise RuntimeError('You got more than one ticket from a ticket_id.'
#                            'Tickets obtained: {}.'.format(tickets))
#
#     tkt = tickets[0]
#     if tkt.ticket.user_id != user.id:
#         return True
#
#     if not tkt.assigned_to:
#         return False
#
#     if tkt.assigned_to == user.email:
#         return False
#     else:
#         return True


###
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--emails',
             action='store_true',
             dest='emails',
             default=False,
             help='Will print user emails.',
        ),

        # make_option('--option',
        #     action='store',
        #     dest='option_attr',
        #     default=0,
        #     type='int',
        #     help='Help text',
        # ),
    )
    def handle(self, *args, **options):
        print('This script does not work anymore, do not use it.')

        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference not specified')

        tkts = get_all_order_tickets(conference)
        if not tkts:
            raise IndexError('Could not find any tickets for conference {}.'.format(conference))

        # unassigned tickets
        un_tkts = [t for t in tkts if not t.p3_conference.assigned_to]

        # users with unassigned tickets
        users = set()
        for ut in un_tkts:
            users.add(ut.user)

        if options['emails']:
            output = sorted([usr.email.encode('utf-8') for usr in users])
        else:
            output = sorted([usr.get_full_name().encode('utf-8') for usr in users])

        if output:
            print(', '.join(output))

