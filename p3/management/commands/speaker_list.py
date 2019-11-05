
""" Print out a listing of speakers.

"""
from django.core.management.base import BaseCommand
from django.core import urlresolvers

from conference import models as cmodels

### Helpers

def profile_url(user):

    return urlresolvers.reverse('conference-profile',
                                args=[user.attendeeprofile.slug])

def speaker_listing(talk):

    return ', '.join(
        '<a href="%s"><i>%s %s</i></a>' % (
            profile_url(speaker.user),
            speaker.user.first_name,
            speaker.user.last_name)
        for speaker in talk.get_all_speakers())

def speaker_name(speaker):

    name = '%s %s' % (
        speaker.user.first_name,
        speaker.user.last_name)

    # Remove whitespace
    return name.strip()

def speaker_list_key(entry):

    speaker = entry[1]
    name = '%s %s' % (
        speaker.user.first_name,
        speaker.user.last_name)

    # Remove whitespace and use title case
    return name.strip().title()

###

class Command(BaseCommand):

    def add_arguments(self, parser):

        # Positional arguments
        parser.add_argument('conference')

        # Named (optional) arguments
        parser.add_argument(
            '--talk_status',
            action='store',
            dest='talk_status',
            default='accepted',
            choices=['accepted', 'proposed', 'canceled'],
            help='The status of the talks to be put in the report. '
                 'Choices: accepted, proposed, canceled',
        )


    def handle(self, *args, **options):
        conference = cmodels.Conference.objects.get(code=options['conference'])
        talks = (
            cmodels.Talk.objects.filter(
                conference=conference.code,
                status=options['talk_status'])
        )

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
        speaker_list = list(speaker_dict.items())
        speaker_list.sort(key=speaker_list_key)

        # Print list of speakers
        self.stdout.write('<h2>Speakers</h2>')
        group = ''
        for entry in speaker_list:
            name, speaker = entry
            sort_name = speaker_list_key(entry)
            if not group:
                group = sort_name[0]
                self.stdout.write('<h3>%s ...</h3>' % group)
                self.stdout.write('<ul>')
            elif group != sort_name[0]:
                self.stdout.write('</ul>')
                group = sort_name[0]
                self.stdout.write('<h3>%s ...</h3>' % group)
                self.stdout.write('<ul>')
            self.stdout.write('<li><a href="%s">%s</a></li>' %
                  (profile_url(speaker.user), name))
        self.stdout.write('</ul>')
        self.stdout.write('<p>%i speakers in total.</p>' % len(speaker_list))
