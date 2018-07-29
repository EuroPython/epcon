# -*- coding: utf-8 -*-
"""
Print out a JSON of accepted talks with the abstracts, schedule and speaker tickets status.
"""
from   django.core.management.base import BaseCommand, CommandError
from   conference   import models

from   p3           import models as p3_models
from   assopy       import models as assopy_models

from   collections  import OrderedDict
from   optparse     import make_option
import simplejson   as json
import traceback

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
        for type_name, session_talks in list(talks.items()):
            if not session_talks:
                continue

            sessions[type_name] = OrderedDict()

            # Sort by talk title using title case
            session_talks.sort(key=lambda talk: clean_title(talk.title).title())
            for talk in session_talks:

                schedule = talk_schedule(talk)
                if not schedule and VERBOSE:
                    print(('ERROR: Talk {} is not scheduled.'.format(talk)))

                if len(schedule) > 1 and VERBOSE:
                    print(('ERROR: Talk {} is scheduled more than once: {}'.format(talk, schedule)))

                sessions[type_name][talk.id] = {
                'id':             talk.id,
                'admin_type':     talk.get_admin_type_display(),
                'type':           talk.get_type_display(),
                'duration':       talk.duration,
                'level':          talk.get_level_display(),
                'track_title':    ', '.join(talk_track_title(talk)),
                'timerange':      ', '.join(schedule),
                'tags':           [str(t) for t in talk.tags.all()],
                'url':            'https://{}.europython.eu/{}'.format(conference, talk.get_absolute_url()),
                'tag_categories': [tag.category for tag in talk.tags.all()],
                'sub_community':  talk.p3_talk.sub_community,
                'title':          clean_title(talk.title),
                'sub_title':      clean_title(talk.sub_title),
                'status':         talk.status,
                'language':       talk.get_language_display(),
                'have_tickets':   have_tickets(talk, conference),
                'abstract_long':  [abst.body for abst in talk.abstracts.all()],
                'abstract_short': talk.abstract_short,
                'abstract_extra': talk.abstract_extra,
                'speakers':       ', '.join(speaker_listing(talk)),
                'companies':      ', '.join(speaker_companies(talk)),
                'emails':         ', '.join(speaker_emails(talk)),
                'twitters':       ', '.join(speaker_twitters(talk)),
                }

                if options['votes']:
                    sessions[type_name][talk.id]['user_votes'] = talk_votes(talk)

        print((json.dumps(sessions, indent=2)))
