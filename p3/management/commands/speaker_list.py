# -*- coding: utf-8 -*-
""" Print out a listing of speakers.

"""
from django.core.management.base import BaseCommand, CommandError
from django.core import urlresolvers
from conference import models
from conference import utils

from collections import defaultdict
from optparse import make_option
import operator

### Globals

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

def speaker_name(speaker):

    name = u'%s %s' % (
        speaker.user.first_name,
        speaker.user.last_name)

    # Remove whitespace
    return name.strip()

def speaker_list_key(entry):

    speaker = entry[1]
    name = u'%s %s' % (
        speaker.user.last_name,
        speaker.user.first_name)

    # Remove whitespace and use title case
    return name.strip().title()

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

        # Find all speakers
        speaker_dict = {}
        for talk in talks:
            for speaker in talk.get_all_speakers():
                name = speaker_name(speaker)
                if not name:
                    continue
                if name.lower() == 'to be announced':
                    continue
                speaker_dict[speaker_name(speaker)] = speaker

        # Prepare list
        speaker_list = speaker_dict.items()
        speaker_list.sort(key=speaker_list_key)

        # Print list of speakers
        print ('<h2>Speakers</h2>')
        group = ''
        for name, speaker in speaker_list:
            sort_name = speaker.user.last_name.strip().title()
            if not group:
                group = sort_name[0]
                print ('<h3>%s ...</h3>' % group)
                print ('<ul>')
            elif group != sort_name[0]:
                print ('</ul>')
                group = sort_name[0]
                print ('<h3>%s ...</h3>' % group)
                print ('<ul>')
            print ((u'<li><a href="%s">%s</a></li>' % (
                profile_url(speaker.user),
                name)).encode('utf-8'))
        print ('</ul>')
        print ('<p>%i speakers in total.</p>' % len(speaker_list))
        
