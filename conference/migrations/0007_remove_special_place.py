
# Generated by Django 1.11.16 on 2019-01-03 20:05
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('conference', '0006_update_talk_model_fields'),
    ]

    operations = [
        migrations.DeleteModel(
            name='SpecialPlace',
        ),
    ]