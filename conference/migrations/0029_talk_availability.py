# Generated by Django 2.2.19 on 2021-04-24 14:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conference', '0028_changes_to_conferencetag_and_conferencetaggeditem'),
    ]

    operations = [
        migrations.AddField(
            model_name='talk',
            name='availability',
            field=models.TextField(blank=True, default='', help_text='<p>Please enter your time availability.</p>', verbose_name='Timezone availability'),
        ),
    ]
