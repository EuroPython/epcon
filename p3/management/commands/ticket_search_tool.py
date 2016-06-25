# -*- coding: utf-8 -*-
"""
    Ticket Search Tool
    ------------------

    Creates a single-page fuzzy full text search list with all tickets
    and their ticket IDs. Write the single page to stdout.

    This can be used during registration to do quick search in the
    list of all tickets in order to find badges or find that no badge
    exists.

"""
import sys

from django.core.management.base import BaseCommand, CommandError
from django.core import urlresolvers
from django.core.exceptions import ObjectDoesNotExist
from conference import models as cmodels
from conference import utils
from p3 import models

from collections import defaultdict
from optparse import make_option
import operator

### Globals

TEMPLATE = u"""\
<!DOCTYPE html>
<html>
<head>
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.10.1/jquery.min.js"></script>
<script src="http://listjs.com/no-cdn/list.js"></script>
<script src="http://listjs.com/no-cdn/list.fuzzysearch.js"></script>
<meta charset=utf-8 />
<title>EuroPython Ticket Search Tool</title>
</head>
<body>
<h2>Attendee Search</h2>
<div id="ticket-list">
<p>
Exact Search: <input type="text" class="search" />
:::
Fuzzy Search: <input type="text" class="fuzzy-search" />
</p>
<p>
<button class="sort" data-sort="name">Sort by name</button>
<button class="sort" data-sort="tid">Sort by ticket ID</button>
</p>
%(listing)s
<script>
var fuzzyOptions = {
  searchClass: "fuzzy-search",
  location: 0,
  distance: 100,
  threshold: 0.1,
  multiSearch: true
};
var ticketList = new List('ticket-list', { 
  valueNames: ['name', 'tid'], 
  plugins: [ListFuzzySearch(fuzzyOptions)]
});
</script>
</body>
</html>
"""

### Helpers

def profile_url(user):

    return urlresolvers.reverse('conference-profile',
                                args=[user.attendeeprofile.slug])

def attendee_name(ticket, profile):

    name = u'%s %s' % (
        profile.user.first_name,
        profile.user.last_name)

    # Remove whitespace
    name = name.strip().title()

    # Use ticket name if not set in profile
    if not name:
        name = ticket.name.strip().title()

    # Use email address if no ticket name set
    if not name:
        name = ticket.p3_conference.assigned_to.strip()

    return name

def attendee_list_key(entry):

    # Sort by name
    return entry[1][2]

###

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        # make_option('--talk_status',
        #      action='store',
        #      dest='talk_status',
        #      default='accepted',
        #      choices=['accepted', 'proposed'],
        #      help='The status of the talks to be put in the report. '
        #           'Choices: accepted, proposed',
        # ),
    )
    def handle(self, *args, **options):
        
        try:
            conference = args[0]
        except IndexError:
            raise CommandError('conference not specified')

        # Get all valid conference tickets (frozen ones are not valid)
        tickets = cmodels.Ticket.objects.filter(
            fare__conference=conference,
            fare__ticket_type='conference',
            orderitem__order___complete=True,
            frozen=False,
            )

        # Find all attendees
        attendee_dict = {}
        for ticket in tickets:
            #sys.stderr.write('ticket %r: conference=%s\n' %
            #                 (ticket, ticket.fare.conference))
            try:
                ticket.p3_conference
            except ObjectDoesNotExist:
                sys.stderr.write('unassigned ticket ID %s: name=%r, '
                                 'user: %s %s\n' %
                                 (ticket.id,
                                  ticket.name,
                                  ticket.user.first_name, ticket.user.last_name))
                continue
            try:
                profile = ticket.p3_conference.profile()
            except ObjectDoesNotExist:
                # Missing profile for assigned user
                sys.stderr.write('could not find profile for %r\n' %
                                 ticket.p3_conference.assigned_to)
                continue
            name = attendee_name(ticket, profile)
            attendee_dict[ticket.id] = (
                ticket,
                profile,
                name)

        # Prepare list
        attendee_list = attendee_dict.items()
        attendee_list.sort(key=attendee_list_key)

        # Print list of attendees
        l = [u'<ul class="list">',
             ]
        for id, (ticket, profile, name) in attendee_list:
            l.append((u'<li>'
                      u'<span class="name">%s</span>: '
                      u'Ticket ID <span class="tid">%s</span>, '
                      u'Ticket code: <span class="tcode">%s</span>'
                      u'</li>' %
                      (name,
                       id,
                       ticket.fare.code)))
        l.extend([u'</ul>',
                  u'<p>%i attendees in total.</p>' % len(attendee_list),
                  ])
        print ((TEMPLATE % {'listing': u'\n'.join(l)}).encode('utf-8'))
