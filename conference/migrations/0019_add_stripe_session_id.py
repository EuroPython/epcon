# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import conference.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conference', '0018_remove_unused_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='stripepayment',
            name='session_id',
            field=models.CharField(max_length=100, null=True),
        ),
    ]
