import csv
import sys
from django.core.management.base import BaseCommand, CommandError
from conference.models import Conference, Talk


def mk_matrix_username(username):
    # Here we have an issue: Matrix does not accept usernames that only
    # contain digits, that start with _, etc. We will try our best to
    # comply.
    if username.isdigit():
        return f'g{username}'
    if username.startswith('_'):
        username = username[1:]
    # Django allows @ but Matrix does not.
    if '@' in username:
        username = username.replace('@', '')
    # Matrix does not like usernames longer than 255 chars
    if len(username) > 255:
        username = username[:255]
    # We still need some chars
    if not username:
        raise ValueError('Invalid username')
    return username


def get_speakers_for_conference(conference=None):
    speakers = set()
    if conference is None:
        conference = Conference.objects.current()

    talks = Talk.objects.accepted(conference)
    for talk in talks:
        speakers |= set(talk.get_all_speakers())
    return speakers


def csv_print(speakers, file=sys.stdout):
    writer = csv.writer(file)
    for speaker in speakers:
        writer.writerow([
            speaker.user.first_name,
            speaker.user.last_name,
            speaker.user.username,
            speaker.user.email,
            f'@{mk_matrix_username(speaker.user.username)}:europython.eu'
        ])


class Command(BaseCommand):
    """
    Get the list of speakers for the given conference (defaults to the current
    conference).

    Output first name, last name, username, email, matrix userid to STDOUT in
    CSV format.

    Optional Argument: --conference=epYEAR (e.g. --conference=ep2019)
    """
    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('--conference', default=None)

    def handle(self, *args, **options):
        try:
            conference = options['conference']
        except KeyError:
            raise CommandError('conference not specified')
        csv_print(get_speakers_for_conference(conference))
