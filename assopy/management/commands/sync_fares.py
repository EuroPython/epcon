from django.core.management.base import BaseCommand, CommandError
from conference import models
from assopy.clients import genro

class Command(BaseCommand):
    help = "Sincronizza le tariffe presenti in conference con il backend remoto"
    def handle(self, *args, **options):
        try:
            conf = args[0]
        except IndexError:
            raise CommandError('codice conferenza non specificato')

        for f in models.Fare.objects.filter(conference=conf):
            if not f.code.startswith('_'):
                print '*', f.code, f.name
                genro.update_fare(f)
