from django.core.management.base import BaseCommand, CommandError
from conference import models as cmodels


def make_speaker_profiles_public_for_conference(conference):

    # Get speaker records
    speakers = set()
    talks = cmodels.Talk.objects.accepted(conference)
    for t in talks:
        speakers |= set(t.get_all_speakers())

    for speaker in speakers:
        user = speaker.user
        profile = cmodels.AttendeeProfile.objects.get(user=user)
        if profile.visibility != 'p':
            print('Setting profile %r to public' % profile)
            profile.visibility = 'p'
            profile.save()


class Command(BaseCommand):
    """
    When accepting talks via database updates, the speaker profiles are
    not automatically set to public.  This command fixes this.

    Argument: <conference year>
    """
    def add_arguments(self, parser):

        # Positional arguments
        parser.add_argument('conference')

    def handle(self, *args, **options):
        try:
            conference = options['conference']
        except KeyError:
            raise CommandError('conference not specified')
        make_speaker_profiles_public_for_conference(conference)
