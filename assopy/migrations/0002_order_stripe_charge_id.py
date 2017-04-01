# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assopy', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='stripe_charge_id',
            field=models.CharField(max_length=64, unique=True, null=True, verbose_name='Charge Stripe ID'),
        ),
    ]
