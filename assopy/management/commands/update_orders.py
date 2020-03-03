import logging
from optparse import make_option

from django.db import transaction
from django.db.models import Q
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from assopy import models

log = logging.getLogger('assopy')

class Command(BaseCommand):
    help = "Gestore ordini; aggiorna gli ordini locali con il backend remoto e cancella gli ordini incompleti troppo vecchi"
    args = "action"
    option_list = BaseCommand.option_list + (
        make_option('--conference',
            action='store',
            dest='conference',
            default=None,
        ),
        make_option('--older-than',
            action='store',
            dest='older_than',
            default='30:bank;3',
            help='Delete incomplete orders older than...',
        ),
    )
    def handle(self, *args, **options):
        try:
            action = getattr(self, '_' + args[0])
        except (IndexError, AttributeError):
            raise CommandError('unknown action')
        return action(*args[1:], **options)

    @transaction.atomic
    def _sync(self, *args, **options):
        if options['conference']:
            qs = models.Order.objects.filter(orderitem__ticket__fare__conference=options['conference'])
        else:
            qs = models.Order.objects.all()
        if args:
            q = Q()
            for x in args:
                q |= Q(code__contains=x)
            qs = qs.filter(q)

        # Tutti gli altri ordini devono essere controllati.
        # Controllo per eventuali variazioni di fattura sia gli ordini completi
        # che quelli incompleti: questi ultimi potrebbero avere una fattura
        # associata anche se non sono marcati come completi
        for o in qs.exclude(assopy_id=''):
            o.complete(ignore_cache=True)

    @transaction.atomic
    def _delete(self, *args, **options):
        older_than = {}
        for rule in options['older_than'].split(';'):
            if ':' in rule:
                days, method = [x.strip() for x in rule.split(':', 1)]
            else:
                days = rule
                method = None
            try:
                older_than[method] = int(days)
            except ValueError:
                raise CommandError('invalid int value: %s' % days)

        default = older_than.get(None)
        today = timezone.now()
        if options['conference']:
            qs = models.Order.objects.filter(orderitem__ticket__fare__conference=options['conference'])
        else:
            qs = models.Order.objects.all()
        for o in qs.exclude(assopy_id=None).filter(_complete=False):
            limit = older_than.get(o.method, default)
            if limit is None:
                continue
            # Non voglio cancellare degli ordini che hanno una fattura
            # collegata, in teoria basterebbe interrogare il backend, ma la
            # .count(); utilizzo la chiamata remota solo per essere sicuro che
            # non sia stata registrata una fattura tra due sincornizzazioni (v.
            # _sync)
            if o.invoices.count() > 0:
                continue
            if (today - o.created).days >= limit:
                log.info('remove "%s" method=%s created=%s', o, o.method, o.created)
                for item in o.orderitem_set.exclude(ticket=None):
                    item.ticket.delete()
                o.delete()
