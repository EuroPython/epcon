# -*- coding: UTF-8 -*-
import os.path
import subprocess
import urlparse
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import reverse

from assopy import models

class Command(BaseCommand):
    help = "generazione voucher"
    option_list = BaseCommand.option_list + (
        make_option('--output',
            action='store',
            dest='output',
            default='.',
            help='Output directory',
        ),
        make_option('--session_id',
            action='store',
            dest='session_id',
            default='',
            help='session id (if needed)',
        ),
    )
    def handle(self, *args, **options):
        try:
            conf = args[0]
        except IndexError:
            raise CommandError('codice conferenza non specificato')

        qs = models.OrderItem.objects\
                .filter(order___complete=True)\
                .filter(ticket__fare__payment_type='v', ticket__fare__conference=conf)\
                .select_related('order__user', 'ticket')
        for item in qs:
            name = item.ticket.name or item.order.user.name()

            fname = '%s - %s (%s).html' % (name, unicode(item.ticket), item.ticket.id)
            fpath = os.path.join(options['output'], fname.encode('utf-8'))

            upath = reverse('assopy-orderitem-voucher', kwargs={'order_id': item.order_id, 'item_id': item.id})
            url = urlparse.urljoin(settings.DEFAULT_URL_PREFIX, upath)
            cmdline = [ 'wkhtmltopdf', '--print-media-type' ]
            if options['session_id']:
                cmdline += [ '--cookie', settings.SESSION_COOKIE_NAME, options['session_id'] ]
            cmdline += [ url, fpath ]
            print fpath
            p = subprocess.Popen(cmdline, close_fds=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            p.communicate()
