# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assopy', '0002_order_stripe_charge_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='issuer',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='invoice',
            name='invoice_copy_full_html',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
