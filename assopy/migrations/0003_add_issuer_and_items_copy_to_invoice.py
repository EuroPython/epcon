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
            name='items_copy',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='order',
            name='cf_code',
            field=models.CharField(max_length=16, verbose_name='Fiscal Code', blank=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='cf_code',
            field=models.CharField(help_text='Needed only for Italian customers', max_length=16, verbose_name='Fiscal Code', blank=True),
        ),
    ]
