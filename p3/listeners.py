# -*- coding: UTF-8 -*-
from email_template import utils
from assopy.models import order_created, purchase_completed

def on_order_created(sender, **kwargs):
    if sender.method == 'bank':
        utils.email(
            'bank-order-complete',
            ctx={'order': sender,},
            to=[sender.user.user.email]
        ).send()

order_created.connect(on_order_created)

def on_purchase_completed(sender, **kwargs):
    try:
        utils.email(
            'purchase-complete',
            ctx={
                'order': sender,
                'student': sender.orderitem_set.filter(ticket__fare__recipient_type='s').count() > 0,
            },
            to=[sender.user.user.email],
        ).send()
    except Exception, e:
        print e
        raise

purchase_completed.connect(on_purchase_completed)
