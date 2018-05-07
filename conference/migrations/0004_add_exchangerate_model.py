# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conference', '0003_add_domain_level_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExchangeRate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('datestamp', models.DateField()),
                ('currency', models.CharField(max_length=3)),
                ('rate', models.DecimalField(max_digits=10, decimal_places=5)),
            ],
        ),
        migrations.AlterField(
            model_name='talk',
            name='domain',
            field=models.CharField(default=b'', max_length=20, choices=[(b'business_track', b'Business Track'), (b'devops', b'DevOps'), (b'django', b'Django Track'), (b'education', b'Educational Track'), (b'general', b'General Python'), (b'hw_iot', b'Hardware/IoT Track'), (b'pydata', b'PyData Track'), (b'science', b'Science Track'), (b'web', b'Web Track'), (b'', b'Other')]),
        ),
    ]
