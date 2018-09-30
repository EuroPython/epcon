# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assopy', '0006_add_bank_to_payment_options'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='User',
            new_name='AssopyUser',
        ),
    ]
