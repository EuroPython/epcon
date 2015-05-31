# -*- coding: utf-8 -*-
""" Print out a listing of accepted talks.

"""
from django.core.management.base import BaseCommand, CommandError
from django.core import urlresolvers
from conference import models
from conference import utils

from collections import defaultdict
from optparse import make_option
import operator

### Globals

TYPE_NAMES = (
    (('keynote', 'Keynote'),
     ) +
    tuple(models.TALK_TYPE)[:] +
    (('europython', 'EuroPython session'),
     ))

### Helpers

def profile_url(user):

    return urlresolvers.reverse('conference-profile',
                                args=[user.attendeeprofile.slug])

def speaker_listing(talk):

    return u', '.join(
        u'<a href="%s"><i>%s %s</i></a>' % (
            profile_url(speaker.user),
            speaker.user.first_name,
            speaker.user.last_name)
        for speaker in talk.get_all_speakers())

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

        # Print list of submissions
        print ('<h2>Accepted submissions</h2>')
        for type, type_name in TYPE_NAMES:
            bag = talk_types.get(type, [])
            if not bag:
                continue
            # Sort by talk title using title case
            bag.sort(key=lambda talk: talk.title.title())
            print ('')
            print ('<h3>%ss</h3>' % type_name)
            print ('<ul>')
            for talk in bag:
                print ((u'<li><a href="%s">%s</a> by %s</li>' % (
                    talk.get_absolute_url(),
                    talk.title,
                    speaker_listing(talk))
                    ).encode('utf-8'))
            print ('</ul>')
        
