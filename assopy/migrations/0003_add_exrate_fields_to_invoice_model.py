# -*- coding: utf-8 -*-


from django.db import migrations, models
import datetime
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('assopy', '0002_auto_20180408_2337'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='exchange_rate',
            field=models.DecimalField(default=Decimal('1'), max_digits=10, decimal_places=5),
        ),
        migrations.AddField(
            model_name='invoice',
            name='exchange_rate_date',
            field=models.DateField(default=datetime.date(2000, 1, 1)),
        ),
        migrations.AddField(
            model_name='invoice',
            name='local_currency',
            field=models.CharField(default=b'EUR', max_length=3),
        ),
        migrations.AddField(
            model_name='invoice',
            name='vat_in_local_currency',
            field=models.DecimalField(default=Decimal('0'), max_digits=6, decimal_places=2),
        ),
    ]
