# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-02-09 10:46
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0002_make_message_attachment_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='is_internal_note',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='message',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='conversations.Message', to_field='uuid'),
        ),
        migrations.AlterField(
            model_name='attachment',
            name='uuid',
            field=models.UUIDField(default=uuid.UUID('a5230bf7-51fc-4c2c-8fa4-d712a3fe3ceb')),
        ),
        migrations.AlterField(
            model_name='message',
            name='thread',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='conversations.Thread'),
        ),
    ]
