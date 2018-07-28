# -*- coding: utf-8 -*-
""" Export a Guidebook schedule CSV file with the currently accepted
    talks.

    Usage: manage.py guidebook_csv ep2015 gb.csv

    Guidebook CSV format (UTF-8 encoded):
    -------------------------------------

    Session Title,Date,Time Start,Time End,Room/Location,Schedule Track (Optional),Description (Optional)
    Sample Session:  Opening Remarks,4/21/11,10:00 AM,11:00 AM,Main Events,Key Event,The conference chairman will be kicking off the event with opening remarks.
    Sample Session:  Presentation XYZ,4/21/11,4:00 PM,6:00 PM,Room 101,Key Event; Track 1,John Doe will be presenting on XYZ.

"""
from django.core.management.base import BaseCommand, CommandError
from django.core import urlresolvers
from django.utils.html import strip_tags
from conference import models

import datetime

### Globals

# Talk .type values, name, description
TYPE_NAMES = (
    ('keynote', 'Keynote', ''),
    ('s', 'Talk', ''),
    ('t', 'Training', ''),
    ('p', 'Poster session', ''),
    ('h', 'Help desk', 'Help desks provide slots for attendee to discuss their problems one-on-one with experts from the projects.'),
    ('europython', 'EuroPython session', 'The EuroPython sessions are intended for anyone interested in helping with the EuroPython organization in the coming years.'),
    ('i', 'Other session', ''),
    )

def _check_talk_types(type_names):
    d = set(x[0] for x in type_names)
    for code, entry in models.TALK_TYPE:
        assert code in d, 'Talk type code %r is missing' % code
_check_talk_types(TYPE_NAMES)

# Headers to use for the GB CSV file
GB_HEADERS = (
    'Session Title',
    'Date', # in format MM/DD/YYYY
    'Time Start', # in format HH:MM AM/PM
    'Time End', # in format HH:MM AM/PM
    'Room/Location', # String
    'Schedule Track (Optional)', # String
    'Description (Optional)', # String
    )

# Poster sessions don't have events associated with them, so use these
# defaults
POSTER_START = datetime.datetime(2015,7,21,17,30)
POSTER_DURATION = datetime.timedelta(minutes=90)
POSTER_ROOM = u'Exhibition Hall'

### Helpers

def profile_url(user):

    return urlresolvers.reverse('conference-profile',
                                args=[user.attendeeprofile.slug])

def speaker_listing(talk):

    return u', '.join(
        u'<i>%s %s</i>' % (
            speaker.user.first_name,
            speaker.user.last_name)
        for speaker in talk.get_all_speakers())

def format_text(text, remove_tags=False):

    # Remove whitespace
    text = text.strip()
    if not text:
        return text

    # Remove links, tags, etc.
    if remove_tags:
        text = strip_tags(text)

    # Remove quotes
    if text[0] == '"' and text[-1] == '"':
        text = text[1:-1]

    return text    

def talk_title(talk):

    title = format_text(talk.title, remove_tags=True)
    if not title:
        return title
    return title + ' [%s]' % talk.pk

def talk_abstract(talk):

    return 'By %s\n\n%s' % (
        speaker_listing(talk),
        format_text(talk.getAbstract().body))

def event_title(event):

    title = format_text(event.custom, remove_tags=True)
    if not title:
        return title
    return title + ' [%s]' % event.pk

def event_abstract(event):

    return format_text(event.abstract)

def add_event(data, talk=None, event=None, session_type='', talk_events=None):

    # Determine title and abstract
    title = ''
    abstract = ''
    if talk is None:
        if event is None:
            raise TypeError('need either talk or event given')
        title = event_title(event)
        abstract = event_abstract(event)
    else:
        title = talk_title(talk)
        abstract = talk_abstract(talk)
        if event is None:
            event = talk.get_event()

    # Determine time_range and room
    if event is None:
        if talk.type and talk.type == 'p':
            # Poster session
            time_range = (POSTER_START,
                          POSTER_START + POSTER_DURATION)
            room = POSTER_ROOM
        else:
            print ('Talk %r (type %r) does not have an event '
                   'associated with it; skipping' %
                   (title, type))
            return
    else:
        time_range = event.get_time_range()
        tracks = event.tracks.all()
        if tracks:
            room = tracks[0].title
        else:
            room = u''
        if talk_events is not None:
            talk_events[event.pk] = event
        
    # Don't add entries for events without title
    if not title:
        return

    # Format time entries
    date = time_range[0].strftime('%m/%d/%Y')
    start_time = time_range[0].strftime('%I:%M %p')
    stop_time = time_range[1].strftime('%I:%M %p')
    
    data.append((
        title,
        date,
        start_time,
        stop_time,
        room,
        session_type,
        abstract,
        ))
    

###

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
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
        try:
            csv_file = args[1]
        except IndexError:
            raise CommandError('CSV file not specified')

        talks = (models.Talk.objects
                 .filter(conference=conference,
                         status='accepted'))

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

        # Create CSV
        data = []
        talk_events = {}
        for type, type_name, description in TYPE_NAMES:

            # Get bag with talks
            bag = talk_types.get(type, [])
            if not bag:
                continue
            
            # Sort by talk title using title case
            bag.sort(key=lambda talk: talk_title(talk).title())

            # Add talks from bag to csv
            for talk in bag:
                add_event(data, talk=talk, talk_events=talk_events, session_type=type_name)

        # Add events which are not talks
        for schedule in models.Schedule.objects.filter(conference=conference):
            for event in models.Event.objects.filter(schedule=schedule):
                if event.pk in talk_events:
                    continue
                add_event(data, event=event)
                
        # Output CSV data, UTF-8 encoded
        data.insert(0, GB_HEADERS)
        with open(csv_file, 'wb') as f:
            for row in data:
                csv_data = (u'"%s"' % (unicode(x).replace(u'"', u'""'))
                            for x in row)
                f.write(u','.join(csv_data).encode('utf-8'))
                f.write('\n')

