# -*- coding: UTF-8 -*-


from django.core.management.base import BaseCommand
from assopy import models as amodels

def generate_invoices_for_zero_amount_orders_for_year(year):
    orders = amodels.Order.objects.filter(
        created__year=year,
        method='bank',
        )
    for o in orders:
        if not o.complete():
            continue
        if o.total() > 0:
            continue
        print ('Creating invoice for order %r' % o)
        o.confirm_order(o.created)
        o.complete()

class Command(BaseCommand):
    """
    The system did not generate invoices for orders with a zero amount
    in 2018 (e.g. as result of using discounts).
    
    We have to add them after the fact.
    """
    def handle(self, *args, **options):
        generate_invoices_for_zero_amount_orders_for_year(2018)
