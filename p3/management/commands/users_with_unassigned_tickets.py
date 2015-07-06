# -*- coding: utf-8 -*-
""" Print information of the users who got unassigned tickets."""

from   django.core.management.base import BaseCommand, CommandError
from   django.core  import urlresolvers
from   conference   import models
from   conference   import utils

from   p3           import models as p3_models
from   conference   import models as conf_models
from   assopy       import models as assopy_models

from   collections  import defaultdict, OrderedDict
from   optparse     import make_option
import operator
import simplejson   as json
import traceback

### Globals

### Helpers
def get_all_order_tickets():
    orders          = assopy_models.Order.objects.filter(_complete=True)
    order_tkts      = [ordi.ticket for order in orders for ordi in order.orderitem_set.all() if ordi.ticket is not None]
    conf_order_tkts = [ot for ot in order_tkts if ot.fare.code.startswith('T')]
    return conf_order_tkts

def get_assigned_ticket(ticket_id):
    return p3_models.TicketConference.objects.filter(ticket=ticket_id)

def has_assigned_ticket(ticket_id):
    return bool(get_assigned_ticket(ticket_id))

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
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference not specified')

        tkts = get_all_order_tickets()

        # unassigned tickets
        un_tkts = [t for t in tkts if not has_assigned_ticket(t.id)]

        # users with unassigned tickets
        users = set()
        for ut in un_tkts:
            users.add(ut.user)

        output = []
        if options['emails']:
            output = sorted([usr.email.encode('utf-8') for usr in users])

        else:
            output = sorted([usr.get_full_name().encode('utf-8') for usr in users])

        #for ot in order_tkts:
        #    tkt = get_conference_ticket(ot.id)

        #from IPython.core.debugger import Tracer
        #Tracer()()

        print(', '.join(output))
