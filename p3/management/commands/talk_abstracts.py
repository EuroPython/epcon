# -*- coding: utf-8 -*-
"""
Print out a JSON of accepted talks with the abstracts, schedule and speaker tickets status.
"""
from   django.core.management.base import BaseCommand, CommandError

from   collections  import OrderedDict
from   optparse     import make_option
import simplejson   as json

from ...utils import(speaker_companies,
                     speaker_listing,
                     speaker_emails,
                     speaker_twitters,
                     have_tickets,
                     talk_schedule,
                     talk_track_title,
                     talk_votes,
                     group_all_talks_by_admin_type,
                     clean_title,
                     )

### Globals
VERBOSE = False


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--verbose',
             action='store_true',
             dest='verbose',
             help='Will output some warning while running.',
        ),
        make_option('--talk_status',
             action='store',
             dest='talk_status',
             default='proposed',
             choices=['accepted', 'proposed', 'canceled'],
             help='The status of the talks to be put in the report. '
                  'Choices: accepted, proposed, canceled',
        ),
        make_option('--votes',
             action='store_true',
             dest='votes',
             default=False,
             help='Add the votes to each talk.',
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

        VERBOSE = options['verbose']

        talks = group_all_talks_by_admin_type(conference, options['talk_status'])

        sessions = OrderedDict()
        # Print list of submissions
        for type_name, session_talks in talks.items():
            if not session_talks:
                continue

            sessions[type_name] = OrderedDict()

            # Sort by talk title using title case
            session_talks.sort(key=lambda talk: clean_title(talk.title).encode('utf-8').title())
            for talk in session_talks:

                schedule = talk_schedule(talk)
                if not schedule and VERBOSE:
                    print('ERROR: Talk {} is not scheduled.'.format(talk))

                if len(schedule) > 1 and VERBOSE:
                    print('ERROR: Talk {} is scheduled more than once: {}'.format(talk, schedule))

                sessions[type_name][talk.id] = {
                'id':             talk.id,
                'admin_type':     talk.get_admin_type_display().encode('utf-8'),
                'type':           talk.get_type_display().encode('utf-8'),
                'duration':       talk.duration,
                'level':          talk.get_level_display().encode('utf-8'),
                'track_title':    ', '.join(talk_track_title(talk)).encode('utf-8'),
                'timerange':      ', '.join(schedule).encode('utf-8'),
                'tags':           [str(t) for t in talk.tags.all()],
                'url':            u'https://{}.europython.eu/{}'.format(conference, talk.get_absolute_url()).encode('utf-8'),
                'tag_categories': [tag.category.encode('utf-8') for tag in talk.tags.all()],
                'sub_community':  talk.p3_talk.sub_community.encode('utf-8'),
                'title':          clean_title(talk.title).encode('utf-8'),
                'sub_title':      clean_title(talk.sub_title).encode('utf-8'),
                'status':         talk.status.encode('utf-8'),
                'language':       talk.get_language_display().encode('utf-8'),
                'have_tickets':   have_tickets(talk, conference),
                'abstract_long':  [abst.body.encode('utf-8') for abst in talk.abstracts.all()],
                'abstract_short': talk.abstract_short.encode('utf-8'),
                'abstract_extra': talk.abstract_extra.encode('utf-8'),
                'speakers':       u', '.join(speaker_listing(talk)).encode('utf-8'),
                'companies':      u', '.join(speaker_companies(talk)).encode('utf-8'),
                'emails':         u', '.join(speaker_emails(talk)).encode('utf-8'),
                'twitters':       u', '.join(speaker_twitters(talk)).encode('utf-8'),
                }

                if options['votes']:
                    sessions[type_name][talk.id]['user_votes'] = talk_votes(talk)

        print(json.dumps(sessions, indent=2))
