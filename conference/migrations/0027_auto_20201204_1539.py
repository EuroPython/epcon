# Generated by Django 2.2.17 on 2020-12-04 14:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conference', '0026_auto_20201204_1130'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conferencetag',
            name='name',
            field=models.CharField(max_length=100, unique=True, verbose_name='Name'),
        ),
        migrations.AlterField(
            model_name='conferencetag',
            name='slug',
            field=models.SlugField(max_length=100, unique=True, verbose_name='Slug'),
        ),
        migrations.AlterField(
            model_name='conferencetaggeditem',
            name='content_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conference_conferencetaggeditem_tagged_items', to='contenttypes.ContentType', verbose_name='Content type'),
        ),
        migrations.AlterField(
            model_name='conferencetaggeditem',
            name='object_id',
            field=models.IntegerField(db_index=True, verbose_name='Object id'),
        ),
    ]
