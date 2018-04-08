# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import markitup.fields


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0016_auto_20160608_1535'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarkitUpPluginModel',
            fields=[
                ('cmsplugin_ptr', models.OneToOneField(parent_link=True, related_name='cms_utils_markituppluginmodel', auto_created=True, primary_key=True, serialize=False, to='cms.CMSPlugin')),
                ('body', markitup.fields.MarkupField(no_rendered_field=True)),
                ('_body_rendered', models.TextField(editable=False, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=('cms.cmsplugin',),
        ),
    ]
