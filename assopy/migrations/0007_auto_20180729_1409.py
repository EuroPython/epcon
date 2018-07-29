# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assopy', '0006_add_bank_to_payment_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='method',
            field=models.CharField(max_length=6, choices=[(b'cc', b'Credit Card'), (b'bank', b'Bank')]),
        ),
    ]
