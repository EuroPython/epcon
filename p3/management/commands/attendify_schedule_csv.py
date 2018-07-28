# -*- coding: utf-8 -*-
""" Export a Attendify schedule CSV file with the currently accepted
    talks.

    Usage: manage.py attendify_schedule_csv ep2016 schedule.csv

    Attendify CSV format (UTF-8 encoded):
    -------------------------------------

    Session Title, Date (MM/DD/YYYY), Start Time (HH:MM), End Time (HH:MM), Description (Optional), Location (Optional), Track Title (Optional), UID (do not delete)

    NOTE: THIS SCRIPT SHOULD ONLY BE USED AS FALLBACK SOLUTION. Please
    use the newer attendify_schedule_xlsx.py command instead.

"""
from django.core.management.base import BaseCommand, CommandError
from django.core import urlresolvers
from django.utils.html import strip_tags
from conference import models

import datetime
import markdown2

### Globals

# These must match the talk .type or .admin_type
from accepted_talks import TYPE_NAMES

# Headers to use for the Attendify CSV file
CSV_HEADERS = (
    'Session Title',
    'Date', # in format MM/DD/YYYY
    'Start Time', # in format HH:MM
    'End Time', # in format HH:MM
    'Description (Optional)', # String
    'Location (Optional)', # String
    'Track Title (Optional)', # String
    'UID (do not delete)', # String
    )

# Poster sessions don't have events associated with them, so use these
# defaults
POSTER_START = datetime.datetime(2016,7,19,15,15) # TBD
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

def format_text(text, remove_tags=False, output_html=True):

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

    # Convert markdown markup to HTML
    if output_html:
        text = markdown2.markdown(text)

    return text    

def talk_title(talk):

    title = format_text(talk.title, remove_tags=True, output_html=False)
    if not title:
        return title
    return title

def talk_abstract(talk):

    return '<p>By %s</p>\n\n%s' % (
        speaker_listing(talk),
        format_text(talk.getAbstract().body))

def event_title(event):

    title = format_text(event.custom, remove_tags=True, output_html=False)
    if not title:
        return title
    return title

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
        if talk.type and talk.type[:1] == 'p':
            # Poster session
            time_range = (POSTER_START,
                          POSTER_START + POSTER_DURATION)
            room = POSTER_ROOM
        else:
            print ('Talk %r (type %r) does not have an event '
                   'associated with it; skipping' %
                   (title, talk.type))
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
    start_time = time_range[0].strftime('%H:%M')
    stop_time = time_range[1].strftime('%H:%M')
    
    # UID
    uid = u''
    
    data.append((
        title,
        date,
        start_time,
        stop_time,
        abstract,
        room,
        session_type,
        uid,
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
            talk_type = talk.type[:1]
            admin_type = talk.admin_type[:1]
            if (admin_type == 'm' or 
               'EPS' in talk.title or 
               'EuroPython 20' in talk.title):
                type = 'm'
            elif (admin_type == 'k' or 
                  talk.title.lower().startswith('keynote')):
                #print ('found keynote: %r' % talk)
                type = 'k'
            else:
                type = talk_type
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
        data.insert(0, CSV_HEADERS)
        with open(csv_file, 'wb') as f:
            for row in data:
                csv_data = (u'"%s"' % (unicode(x).replace(u'"', u'""'))
                            for x in row)
                f.write(u','.join(csv_data).encode('utf-8'))
                f.write('\n')

