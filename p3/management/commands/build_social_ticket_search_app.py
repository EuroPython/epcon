
"""
    Build Social Ticket Search App
    ------------------------------

    Creates a single-page fuzzy full text search list with all tickets
    and their social ticket IDs.  Writes the single page to
    ep-social-ticket-search-app/index.html

    This can be used during registration to do quick search in the
    list of all tickets in order to find badges or find that no badge
    exists.

    Usage:
    
    cd epcon
    ./manage.py build_social_ticket_search_app ep2018
    cd ep-social-ticket-search-app
    ./run.sh
    
    This will build the search app and start a web server running
    on port 8000. Pointing a browser at http://localhost:8000/ will
    then load the app into the browser.

    Author: Marc-Andre Lemburg, 2016-2017.

"""
from django.core.management.base import BaseCommand
from conference import models as cmodels

### Globals

TEMPLATE = """\
<!DOCTYPE html>
<html>
<title>EuroPython %(year)s Social Ticket Search App</title>
<meta name="viewport" content="width=device-width, initial-scale=0.9">
<link rel="stylesheet" href="css/materialize.min.css">
<head>
<meta charset=utf-8 />
<title>EuroPython %(year)s Social Ticket Search App</title>
</head>
<body>

<h3 class="center-align hide-on-small-only">EuroPython %(year)s Social Ticket Search App</h3>

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

    # XXX For EP2019, we have to use the ticket.name, since the profile
    #     will be referring to the buyer's profile in many cases due
    #     to a bug in the system.
    #     See https://github.com/EuroPython/epcon/issues/1055

    # Use ticket name if not set in profile
    name = ticket.name.strip()
        
    # Determine user name from profile, if available
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

def create_app_file(conference, output_file):

    output = open(output_file, 'wb')

    # Get all valid conference tickets (frozen ones are not valid)
    tickets = cmodels.Ticket.objects.filter(
        fare__conference=conference,
        fare__ticket_type='event',
        orderitem__order___complete=True,
        frozen=False,
        )

    # Find all attendees
    attendee_dict = {}
    missing_profiles = []
    for ticket in tickets:
        #sys.stderr.write('ticket %r: conference=%s\n' %
        #                 (ticket, ticket.fare.conference))
        profile = None
        email = ticket.user.email
        name = attendee_name(ticket, profile)
        attendee_dict[ticket.id] = (
            ticket,
            profile,
            name,
            email)

    # Prepare list
    attendee_list = list(attendee_dict.items())
    attendee_list.sort(key=attendee_list_key)

    # Print list of attendees
    l = ['<table class="striped">',
         '<thead>',
         '<tr>'
         '<th data-field="name">Name</th>',
         '<th data-field="email" class="hide-on-small-only">Email</th>',
         '<th data-field="tid">TID</th>',
         '<th data-field="tcode" class="hide-on-small-only">Code</th>',
         '</tr>'
         '</thead>',
         '<tbody class="list">',
         ]
    for id, (ticket, profile, name, email) in attendee_list:
        l.append(('<tr>'
                  '<td class="name">%s</td>'
                  '<td class="email hide-on-small-only">%s</td>'
                  '<td class="tid">%s</td>'
                  '<td class="tcode hide-on-small-only">%s</td>'
                  '</tr>' %
                  (name,
                   email,
                   id,
                   ticket.fare.code)))
    l.extend(['</tbody>',
              '</table>',
              '<p>%i attendees in total.</p>' % len(attendee_list),
              ])
    output.write((TEMPLATE % {
                      'listing': '\n'.join(l),
                      'year': conference[2:],
                  }).encode('utf-8'))

###

class Command(BaseCommand):

    args = '<conference> [<output-file>]'

    def add_arguments(self, parser):

        # Positional arguments
        parser.add_argument('conference')
        parser.add_argument('output_file', nargs='?',
                            default='ep-social-ticket-search-app/index.html')

    def handle(self, *args, **options):
        conference = options['conference']
        output_file = options['output_file']

        create_app_file(conference, output_file)
