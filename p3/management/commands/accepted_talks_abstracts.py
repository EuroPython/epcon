# -*- coding: utf-8 -*-
""" Print out a JSON of accepted talks with the abstracts, schedule and speaker tickets status.

"""
from   django.core.management.base import BaseCommand, CommandError
from   django.core  import urlresolvers
from   conference   import models
from   conference   import utils

from   p3           import models as p3_models
from   assopy       import models as assopy_models

from   collections  import defaultdict, OrderedDict
from   optparse     import make_option
import operator
import simplejson   as json
import traceback

### Globals
VERBOSE = False

TYPE_NAMES = (
    ('keynote', 'Keynotes'),
    ('s', 'Talks'),
    ('t', 'Trainings'),
    ('p', 'Poster sessions'),
    ('h', 'Help desks'),
    ('europython', 'EuroPython sessions'),
    ('i', 'Other sessions'),
    )

def _check_talk_types(type_names):
    d = dict(type_names)
    for code, entry in models.TALK_TYPE:
        assert code in d, 'Talk type code %r is missing' % code
_check_talk_types(TYPE_NAMES)

### Helpers
def speaker_listing(talk):
    return u', '.join(
        u'{} {}'.format(speaker.user.first_name, speaker.user.last_name) for speaker in talk.get_all_speakers())


def speaker_emails(talk):
    return u', '.join(
        u'{}'.format(speaker.user.email) for speaker in talk.get_all_speakers())

def get_orders_from(user):
    return assopy_models.Order.objects.filter(_complete=True, user=user.id)

def get_tickets_assigned_to(user):
    return p3_models.TicketConference.objects.filter(assigned_to=user.email)

def is_ticket_assigned_to_someone_else(ticket, user):
    tickets = p3_models.TicketConference.objects.filter(ticket_id=ticket.id)

    if not tickets:
        return False
        #from IPython.core.debugger import Tracer
        #Tracer()()
        #raise RuntimeError('Could not find any ticket with ticket_id {}.'.format(ticket))

    if len(tickets) > 1:
        raise RuntimeError('You got more than one ticket from a ticket_id.'
                           'Tickets obtained: {}.'.format(tickets))

    tkt = tickets[0]
    if tkt.ticket.user_id != user.id:
        return True

    if not tkt.assigned_to:
        return False

    if tkt.assigned_to == user.email:
        return False
    else:
        return True


def has_ticket(user):
    tickets = get_tickets_assigned_to(user)
    if tickets:
        return True

    user_tickets = list(user.ticket_set.all())
    orders = get_orders_from(user)
    if orders:
        order_tkts = [ordi.ticket for order in orders for ordi in order.orderitem_set.all() if ordi.ticket is not None]
        user_tickets.extend(order_tkts)

    for tkt in user_tickets:
        if tkt.fare.code.startswith('T'):
            if not is_ticket_assigned_to_someone_else(tkt, user):
                return True

    return False


def have_tickets(talk):
    usrs = talk.get_all_speakers()
    have_tkt = []
    for user in usrs:
        try:
            have_tkt.append(has_ticket(user.user))
        except:
            print(traceback.format_exc())
            raise

    return have_tkt


def talk_title(talk):

    # Remove whitespace
    title = talk.title.strip()

    # Remove double spaces
    title = title.replace("  ", " ")

    # Remove quotes
    if title[0] == '"' and title[-1] == '"':
        title = title[1:-1]

    return title


def get_talk_events(talk):
    return [event for event in talk.event_set.all() if event.tracks.all()]


def talk_track_title(talk):
    events = get_talk_events(talk)
    if not events:
        return ''

    tracks = [track for event in events for track in event.tracks.all() if event.tracks.all()]
    return ', '.join([tr.title for tr in tracks])


def talk_schedule(talk):
    events = get_talk_events(talk)

    if not events:
        if VERBOSE:
            print('ERROR: Talk {} is not scheduled.'.format(talk))
        return ''

    timeranges = []
    for event in events:
        timerange = event.get_time_range()
        timeranges.append('{}, {}'.format(str(timerange[0]), str(timerange[1])))

    return '; '.join(timeranges)

###
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--verbose',
             action='store_true',
             dest='verbose',
             default=False,
             help='Verbose will print further check results on the status of talks.',
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

        if options['verbose']:
            VERBOSE = True

        talks = (models.Talk.objects
                 .filter(conference=conference,
                         status='accepted'))

        #from IPython.core.debugger import Tracer
        #Tracer()()

        # Group by types
        talk_types = {}
        for talk in talks:
            if 'EPS' in talk.title or 'EuroPython 20' in talk.title:
                type = 'europython'
            elif talk.title.lower().startswith('keynote'):
                type = 'keynote'
            else:
                type = talk.type
            if type in talk_types:
                talk_types[type].append(talk)
            else:
                talk_types[type] = [talk]

        sessions = OrderedDict()
        # Print list of submissions
        for type, type_name in TYPE_NAMES:
            bag = talk_types.get(type, [])
            if not bag:
                continue

            sessions[type_name] = OrderedDict()

            # Sort by talk title using title case
            bag.sort(key=lambda talk: talk_title(talk).title())
            for talk in bag:

                sessions[type_name][talk.id] = {
                'id':           talk.id,
                'duration':     talk.duration,
                'track_title':  talk_track_title(talk),
                'timerange':    talk_schedule(talk).encode('utf-8'),
                'tags':         [str(t) for t in talk.tags.all()],
                'title':        talk_title(talk).encode('utf-8'),
                'speakers':     speaker_listing(talk).encode('utf-8'),
                'emails':       speaker_emails(talk).encode('utf-8'),
                'have_tickets': have_tickets(talk),
                'abstracts':    [abst.body.encode('utf-8') for abst in talk.abstracts.all()]}

        print(json.dumps(sessions, indent=2))
