"""
    Build Ticket Search App
    -----------------------

    Creates a single-page fuzzy full text search list with all tickets
    and their ticket IDs.  Writes the single page to
    ep-ticket-search-app/index.html

    This can be used during registration to do quick search in the
    list of all tickets in order to find badges or find that no badge
    exists.

    Usage:
    
    cd epcon
    ./manage.py build_ticket_search_app ep2016
    cd ep-ticket-search-app
    ./run.sh
    
    This will build the search app and start a web server running
    on port 8000. Pointing a browser at http://localhost:8000/ will
    then load the app into the browser.

    Author: Marc-Andre Lemburg, 2016-2021.

"""
import sys
import csv

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from conference import models as cmodels

### Globals

TEMPLATE = """\
<!DOCTYPE html>
<html>
<title>EuroPython %(year)s Ticket Search App</title>
<meta name="viewport" content="width=device-width, initial-scale=0.9">
<link rel="stylesheet" href="css/materialize.min.css">
<head>
<meta charset=utf-8 />
<title>EuroPython %(year)s Ticket Search App</title>
<style>
.sprint {
    color: purple;
}
.training {
    color: blue;
}
.combined {
    color: green;
}
.conference {
    color: red;
}
</style>
</head>
<body>

<h3 class="center-align hide-on-small-only">EuroPython %(year)s Ticket Search App</h3>

<div id="ticket-list" class="container">

<p>
<label for="exact_search" class="hide-on-small-only">Exact search</label>
<input id="exact_search" type="text" class="search" placeholder="Exact search"/>
<label for="fuzzy_search" class="hide-on-small-only">Fuzzy search</label>
<input id="fuzzy_search" type="text" class="fuzzy-search" placeholder="Fuzzy search"/>
</p>

<p class="row">
<button class="sort btn col s5" data-sort="name">Sort by name</button>
<button class="sort btn col s5 offset-s2" data-sort="tid">Sort by ticket ID</button>
</p>

%(listing)s

</div>

<script src="js/jquery.min.js"></script>
<script src="js/jquery.map.min.js"></script>
<script src="js/list.js"></script>
<script src="js/list.fuzzysearch.js"></script>
<script src="js/materialize.min.js"></script>
<script>
var fuzzyOptions = {
  searchClass: "fuzzy-search",
  location: 0,
  distance: 100,
  threshold: 0.1,
  multiSearch: true
};
var ticketList = new List('ticket-list', { 
  valueNames: ['name', 'email', 'tid'], 
  plugins: [ListFuzzySearch(fuzzyOptions)]
});
</script>
</body>
</html>
"""

### Helpers

def attendee_name(ticket, profile=None):

    # Use ticket name if not set in profile
    name = ticket.name.strip()
        
    # Determine user name from profile, if available and ticket.name is not
    # set
    if not name and profile is not None:
        name = '%s %s' % (
            profile.user.first_name,
            profile.user.last_name)
        name = name.strip()

    # Convert to title case, if not an email address
    if '@' not in name:
        name = name.title()

    # Use email address if no ticket name set
    if not name:
        name = ticket.p3_conference.assigned_to.strip()

    return name

def attendee_list_key(entry):

    # Sort by name
    return entry[1][2]

def get_ticket_class(ticket):

    """ Return a ticket class for ticket

        Possible values are:
        - training = training ticket
        - combined = training + conference ticket
        - conference = conference ticket
        - sprint = sprint-only ticket
        - other = other ticket class
    
    """
    if ticket.fare.code.startswith('TRT'):
        ticket_class = 'training'
    elif ticket.fare.code.startswith('TRC'):
        ticket_class = 'combined'
    elif ticket.fare.code.startswith('TRP'):
        ticket_class = 'sprint'
    elif ticket.fare.code.startswith('TRS'):
        ticket_class = 'conference'
    else:
        ticket_class = 'other'
    return ticket_class

def create_app_file(conference,
                    output_file='ep-ticket-search-app/index.html',
                    output_csv='ep-ticket-search-app/data.csv'):

    # Get all valid conference tickets (frozen ones are not valid)
    tickets = cmodels.Ticket.objects.filter(
        fare__conference=conference,
        fare__ticket_type='conference',
        orderitem__order___complete=True,
        frozen=False,
        )

    # Figure out the speakers
    speakers = {}
    accepted_talks = cmodels.Talk.objects.filter(
        conference=conference,
        status='accepted',
    )
    for talk in accepted_talks:
        for speaker in talk.get_all_speakers():
            speakers[speaker.user.email] = speaker

    # Find all attendees
    attendee_dict = {}
    missing_profiles = []
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
        email = ticket.p3_conference.assigned_to
        try:
            profile = ticket.p3_conference.profile()
        except ObjectDoesNotExist:
            # Missing profile for assigned user
            sys.stderr.write('could not find profile for %r\n' %
                             ticket.p3_conference.assigned_to)
            profile = None
        except MultipleObjectsReturned:
            # Profile assigned to multiple user accounts
            sys.stderr.write('multiple users accounts for %r\n' %
                             ticket.p3_conference.assigned_to)
            profile = None
        if ticket.id in attendee_dict:
            # Duplicate ticket.id; should not happen
            sys.stderr.write('duplicate ticket.id %r for %r\n' %
                             (ticket.id, ticket.p3_conference.assigned_to))
        name = attendee_name(ticket, profile)
        is_speaker = (email in speakers)
        attendee_dict[ticket.id] = (
            ticket,
            profile,
            name,
            email,
            is_speaker)

    # Prepare list
    attendee_list = list(attendee_dict.items())
    attendee_list.sort(key=attendee_list_key)

    # Print list of attendees
    l = ['<table class="striped">',
         '<thead>',
         '<tr>'
         '<th data-field="name">Name</th>',
         '<th data-field="email" class="hide-on-small-only">Email</th>',
         '<th data-field="speaker" class="hide-on-small-only">Speaker</th>',
         '<th data-field="tid">TID</th>',
         '<th data-field="tcode" class="hide-on-small-only">Code</th>',
         '</tr>'
         '</thead>',
         '<tbody class="list">',
         ]
    for id, (ticket, profile, name, email, is_speaker) in attendee_list:
        code = ticket.fare.code
        ticket_class = get_ticket_class(ticket)
        l.append(('<tr>'
                  '<td class="name">%s</td>'
                  '<td class="email hide-on-small-only">%s</td>'
                  '<td class="speaker hide-on-small-only">%s</td>'
                  '<td class="tid %s">%s</td>'
                  '<td class="tcode hide-on-small-only">%s</td>'
                  '</tr>' %
                  (name,
                   email,
                   'yes' if is_speaker else 'no',
                   ticket_class,
                   id,
                   ticket.fare.code)))
    l.extend(['</tbody>',
              '</table>',
              '<p>%i tickets in total. '
              'Color coding: '
              '<span class="sprint">TID</span> = Sprint Ticket. '
              '<span class="training">TID</span> = Training Ticket. '
              '<span class="combined">TID</span> = Combined Ticket. '
              '<span class="conference">TID</span> = Conference Ticket.</p>' % 
              len(attendee_list),
              ])
    with open(output_file, 'wb') as fp:
        fp.write((TEMPLATE % {
                      'listing': '\n'.join(l),
                      'year': conference[2:],
                  }).encode('utf-8'))

    # Write CSV output
    with open(output_csv, 'w') as fp:
        writer = csv.writer(fp)
        headers = [
            'name',
            'email',
            'is_speaker',
            'ticket_class',
            'ticket_id',
            'fare_code',
            ]
        writer.writerow(headers)
        for id, (ticket, profile, name, email, is_speaker) in attendee_list:
            code = ticket.fare.code
            ticket_class = get_ticket_class(ticket)
            row = [
                name,
                email,
                'yes' if is_speaker else 'no',
                ticket_class,
                id,
                code,
                ]
            writer.writerow(row)

###

class Command(BaseCommand):

    args = '<conference> [<output-file>]'

    def add_arguments(self, parser):

        # Positional arguments
        parser.add_argument('conference')
        parser.add_argument('output_file', nargs='?',
                            default='ep-ticket-search-app/index.html')
        parser.add_argument('output_csv', nargs='?',
                            default='ep-ticket-search-app/data.csv')

    def handle(self, *args, **options):
        conference = options['conference']
        output_file = options['output_file']
        output_csv = options['output_csv']

        create_app_file(conference, output_file, output_csv)
