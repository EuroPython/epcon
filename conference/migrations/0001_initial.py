
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import conference.models
from django.conf import settings
import taggit.managers
import tagging.fields
import common.django_urls


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0006_require_contenttypes_0002'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AttendeeLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('message', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='AttendeeProfile',
            fields=[
                ('user', models.OneToOneField(primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('slug', models.SlugField(unique=True)),
                ('uuid', models.CharField(unique=True, max_length=6)),
                ('image', models.ImageField(upload_to=conference.models._fs_upload_to(b'profile'), blank=True)),
                ('birthday', models.DateField(null=True, verbose_name='Birthday', blank=True)),
                ('phone', models.CharField(help_text='Enter a phone number where we can contact you in case of administrative issues.<br />Use the international format, eg: +39-055-123456', max_length=30, verbose_name='Phone', blank=True)),
                ('personal_homepage', models.URLField(verbose_name='Personal homepage', blank=True)),
                ('company', models.CharField(max_length=50, verbose_name='Company', blank=True)),
                ('company_homepage', models.URLField(verbose_name='Company homepage', blank=True)),
                ('job_title', models.CharField(max_length=50, verbose_name='Job title', blank=True)),
                ('location', models.CharField(max_length=100, verbose_name='Location', blank=True)),
                ('visibility', models.CharField(default=b'x', max_length=1, choices=[(b'x', b'Private (disabled)'), (b'm', b'Participants only'), (b'p', b'Public')])),
            ],
        ),
        migrations.CreateModel(
            name='Conference',
            fields=[
                ('code', models.CharField(max_length=10, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('cfp_start', models.DateField(null=True, blank=True)),
                ('cfp_end', models.DateField(null=True, blank=True)),
                ('conference_start', models.DateField(null=True, blank=True)),
                ('conference_end', models.DateField(null=True, blank=True)),
                ('voting_start', models.DateField(null=True, blank=True)),
                ('voting_end', models.DateField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='ConferenceTag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100, verbose_name='Name')),
                ('slug', models.SlugField(unique=True, max_length=100, verbose_name='Slug')),
                ('category', models.CharField(default=b'', max_length=50, blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ConferenceTaggedItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.IntegerField(verbose_name='Object id', db_index=True)),
                ('content_type', models.ForeignKey(related_name='conference_conferencetaggeditem_tagged_items', verbose_name='Content type', to='contenttypes.ContentType')),
                ('tag', models.ForeignKey(related_name='conference_conferencetaggeditem_items', to='conference.ConferenceTag')),
            ],
            options={
                'verbose_name': 'Tagged Item',
                'verbose_name_plural': 'Tagged Items',
            },
        ),
        migrations.CreateModel(
            name='Deadline',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField()),
            ],
            options={
                'ordering': ['date'],
            },
        ),
        migrations.CreateModel(
            name='DeadlineContent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language', models.CharField(max_length=3)),
                ('headline', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('deadline', models.ForeignKey(to='conference.Deadline')),
            ],
        ),
        migrations.CreateModel(
            name='DidYouKnow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('visible', models.BooleanField(default=True, verbose_name=b'visible')),
            ],
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_time', models.TimeField()),
                ('custom', models.TextField(help_text=b'title for a custom event (an event without a talk)', blank=True)),
                ('abstract', models.TextField(help_text=b'description for a custom event', blank=True)),
                ('duration', models.PositiveIntegerField(default=0, help_text=b'duration of the event (in minutes). Override the talk duration if present')),
                ('tags', models.CharField(help_text=b'comma separated list of tags. Something like: special, break, keynote', max_length=200, blank=True)),
                ('video', models.CharField(max_length=1000, blank=True)),
                ('bookable', models.BooleanField(default=False)),
                ('seats', models.PositiveIntegerField(default=0, help_text=b'seats available. Override the track default if set')),
            ],
            options={
                'ordering': ['start_time'],
            },
        ),
        migrations.CreateModel(
            name='EventBooking',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('event', models.ForeignKey(to='conference.Event')),
            ],
        ),
        migrations.CreateModel(
            name='EventInterest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('interest', models.IntegerField()),
                ('event', models.ForeignKey(to='conference.Event')),
            ],
        ),
        migrations.CreateModel(
            name='EventTrack',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('event', models.ForeignKey(to='conference.Event')),
            ],
        ),
        migrations.CreateModel(
            name='Fare',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('conference', models.CharField(help_text=b'Conference code', max_length=20)),
                ('code', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('price', models.DecimalField(max_digits=6, decimal_places=2)),
                ('start_validity', models.DateField(null=True, blank=True)),
                ('end_validity', models.DateField(null=True, blank=True)),
                ('recipient_type', models.CharField(default=b'p', max_length=1, choices=[(b'c', b'Company'), (b's', b'Student'), (b'p', b'Personal')])),
                ('ticket_type', models.CharField(default=b'conference', max_length=10, db_index=True, choices=[(b'conference', b'Conference ticket'), (b'partner', b'Partner Program'), (b'event', b'Event'), (b'other', b'Other')])),
                ('payment_type', models.CharField(default=b'p', max_length=1, choices=[(b'p', b'Payment'), (b'v', b'Voucher'), (b'd', b'Deposit')])),
                ('blob', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Hotel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name=b'Name')),
                ('telephone', models.CharField(max_length=50, verbose_name=b'Phone', blank=True)),
                ('url', models.URLField(blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name=b'email', blank=True)),
                ('availability', models.CharField(max_length=50, verbose_name=b'Availability', blank=True)),
                ('price', models.CharField(max_length=50, verbose_name=b'Price', blank=True)),
                ('note', models.TextField(verbose_name=b'note', blank=True)),
                ('affiliated', models.BooleanField(default=False, verbose_name=b'Affiliated')),
                ('visible', models.BooleanField(default=True, verbose_name=b'visibile')),
                ('address', models.CharField(default=b'', max_length=200, verbose_name=b'Address', blank=True)),
                ('lng', models.FloatField(default=0.0, verbose_name=b'longitude', blank=True)),
                ('lat', models.FloatField(default=0.0, verbose_name=b'latitude', blank=True)),
                ('modified', models.DateField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='MediaPartner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('partner', models.CharField(help_text=b'The media partner name', max_length=100)),
                ('slug', models.SlugField()),
                ('url', models.URLField(blank=True)),
                ('logo', models.ImageField(help_text=b'Insert a raster image big enough to be scaled as needed', upload_to=conference.models._fs_upload_to(b'media-partner'), blank=True)),
            ],
            options={
                'ordering': ['partner'],
            },
        ),
        migrations.CreateModel(
            name='MediaPartnerConference',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('conference', models.CharField(max_length=20)),
                ('tags', tagging.fields.TagField(max_length=255, blank=True)),
                ('partner', models.ForeignKey(to='conference.MediaPartner')),
            ],
            options={
                'ordering': ['conference'],
            },
        ),
        migrations.CreateModel(
            name='MultilingualContent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('object_id', models.PositiveIntegerField(db_index=True)),
                ('language', models.CharField(max_length=3)),
                ('content', models.CharField(max_length=20)),
                ('body', models.TextField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
            ],
        ),
        migrations.CreateModel(
            name='Presence',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('conference', models.CharField(max_length=10)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('profile', models.ForeignKey(related_name='presences', to='conference.AttendeeProfile')),
            ],
        ),
        migrations.CreateModel(
            name='Quote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('who', models.CharField(max_length=100)),
                ('conference', models.CharField(max_length=20)),
                ('text', models.TextField()),
                ('activity', models.CharField(max_length=50, blank=True)),
                ('image', models.ImageField(upload_to=conference.models._fs_upload_to(b'quote', b'who'), blank=True)),
            ],
            options={
                'ordering': ['conference', 'who'],
            },
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('conference', models.CharField(help_text=b'nome della conferenza', max_length=20)),
                ('slug', models.SlugField()),
                ('date', models.DateField()),
                ('description', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['date'],
            },
        ),
        migrations.CreateModel(
            name='Speaker',
            fields=[
                ('user', models.OneToOneField(primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
            ],
            bases=(models.Model, common.django_urls.UrlMixin),
        ),
        migrations.CreateModel(
            name='SpecialPlace',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name=b'Name')),
                ('address', models.CharField(default=b'', max_length=200, verbose_name=b'Address', blank=True)),
                ('type', models.CharField(max_length=10, choices=[(b'conf-hq', b'Conference Site'), (b'pyevents', b'PyEvents')])),
                ('url', models.URLField(blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name=b'Email', blank=True)),
                ('telephone', models.CharField(max_length=50, verbose_name=b'Phone', blank=True)),
                ('note', models.TextField(verbose_name=b'note', blank=True)),
                ('visible', models.BooleanField(default=True, verbose_name=b'visibile')),
                ('lng', models.FloatField(default=0.0, verbose_name=b'longitude', blank=True)),
                ('lat', models.FloatField(default=0.0, verbose_name=b'latitude', blank=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Sponsor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sponsor', models.CharField(help_text=b'Name of the sponsor', max_length=100)),
                ('slug', models.SlugField()),
                ('url', models.URLField(blank=True)),
                ('logo', models.ImageField(help_text=b'Insert a raster image big enough to be scaled as needed', upload_to=conference.models._fs_upload_to(b'sponsor'), blank=True)),
                ('alt_text', models.CharField(max_length=150, blank=True)),
                ('title_text', models.CharField(max_length=150, blank=True)),
            ],
            options={
                'ordering': ['sponsor'],
            },
        ),
        migrations.CreateModel(
            name='SponsorIncome',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('conference', models.CharField(max_length=20)),
                ('income', models.PositiveIntegerField()),
                ('tags', tagging.fields.TagField(max_length=255, blank=True)),
                ('sponsor', models.ForeignKey(to='conference.Sponsor')),
            ],
            options={
                'ordering': ['conference'],
            },
        ),
        migrations.CreateModel(
            name='Talk',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=80, verbose_name='Talk title')),
                ('sub_title', models.CharField(default=b'', max_length=1000, verbose_name='Sub title', blank=True)),
                ('slug', models.SlugField(unique=True, max_length=100)),
                ('prerequisites', models.CharField(default=b'', help_text=b'What should attendees know already', max_length=150, verbose_name='prerequisites', blank=True)),
                ('conference', models.CharField(help_text=b'name of the conference', max_length=20)),
                ('admin_type', models.CharField(blank=True, max_length=1, choices=[(b'o', b'Opening session'), (b'c', b'Closing session'), (b'l', b'Lightning talk'), (b'k', b'Keynote'), (b'r', b'Recruiting session'), (b'm', b'EPS session'), (b'p', b'Community session'), (b's', b'Open space'), (b'e', b'Social event'), (b'x', b'Reserved slot'), (b'z', b'Sponsored session')])),
                ('language', models.CharField(default=b'en', max_length=3, verbose_name='Language', choices=[(b'en', b'English')])),
                ('abstract_short', models.TextField(default=b'', help_text='<p>Please enter a short description of the talk you are submitting.</p>', verbose_name='Talk abstract short')),
                ('abstract_extra', models.TextField(default=b'', help_text='<p>Please enter instructions for attendees.</p>', verbose_name='Talk abstract extra')),
                ('slides', models.FileField(upload_to=conference.models._fs_upload_to(b'slides'), blank=True)),
                ('video_type', models.CharField(blank=True, max_length=30, choices=[(b'viddler_oembed', b'oEmbed (Youtube, Vimeo, ...)'), (b'download', b'Download')])),
                ('video_url', models.TextField(blank=True)),
                ('video_file', models.FileField(upload_to=conference.models._fs_upload_to(b'videos'), blank=True)),
                ('teaser_video', models.URLField(help_text='Insert the url for your teaser video', verbose_name='Teaser video', blank=True)),
                ('status', models.CharField(max_length=8, choices=[(b'proposed', 'Proposed'), (b'accepted', 'Accepted'), (b'canceled', 'Canceled')])),
                ('level', models.CharField(default=b'beginner', max_length=12, verbose_name='Audience level', choices=[(b'beginner', 'Beginner'), (b'intermediate', 'Intermediate'), (b'advanced', 'Advanced')])),
                ('training_available', models.BooleanField(default=False)),
                ('type', models.CharField(default=b't_30', max_length=5, choices=[(b't_30', b'Talk (30 mins)'), (b't_45', b'Talk (45 mins)'), (b't_60', b'Talk (60 mins)'), (b'i_60', b'Interactive (60 mins)'), (b'r_180', b'Training (180 mins)'), (b'p_180', b'Poster session (180 mins)'), (b'n_60', b'Panel (60 mins)'), (b'n_90', b'Panel (90 mins)'), (b'h_180', b'Help desk (180 mins)')])),
                ('duration', models.IntegerField(default=0, help_text='This is the duration of the talk. Set to 0 to use the default talk duration.', verbose_name='Duration')),
                ('suggested_tags', models.CharField(max_length=100, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['title'],
            },
            bases=(models.Model, common.django_urls.UrlMixin),
        ),
        migrations.CreateModel(
            name='TalkSpeaker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('helper', models.BooleanField(default=False)),
                ('speaker', models.ForeignKey(to='conference.Speaker')),
                ('talk', models.ForeignKey(to='conference.Talk')),
            ],
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='Attendee name, i.e. the person who will attend the conference.', max_length=60, blank=True)),
                ('frozen', models.BooleanField(default=False, help_text='If a ticket was canceled or otherwise needs to be marked as invalid, please check this checkbox to indicate this.', verbose_name='ticket canceled / invalid / frozen')),
                ('ticket_type', models.CharField(default=b'standard', max_length=8, choices=[(b'standard', b'standard'), (b'staff', b'staff')])),
                ('fare', models.ForeignKey(to='conference.Fare')),
                ('user', models.ForeignKey(help_text='Buyer of the ticket', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('track', models.CharField(max_length=20, verbose_name=b'nome track')),
                ('title', models.TextField(help_text=b'HTML supportato', verbose_name=b'titolo della track')),
                ('seats', models.PositiveIntegerField(default=0)),
                ('order', models.PositiveIntegerField(default=0, verbose_name=b'ordine')),
                ('translate', models.BooleanField(default=False)),
                ('outdoor', models.BooleanField(default=False)),
                ('schedule', models.ForeignKey(to='conference.Schedule')),
            ],
        ),
        migrations.CreateModel(
            name='VotoTalk',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('vote', models.DecimalField(max_digits=5, decimal_places=2)),
                ('talk', models.ForeignKey(to='conference.Talk')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Talk voting',
                'verbose_name_plural': 'Talk votings',
            },
        ),
        migrations.AddField(
            model_name='talk',
            name='speakers',
            field=models.ManyToManyField(to='conference.Speaker', through='conference.TalkSpeaker'),
        ),
        migrations.AddField(
            model_name='talk',
            name='tags',
            field=taggit.managers.TaggableManager(to='conference.ConferenceTag', through='conference.ConferenceTaggedItem', help_text='A comma-separated list of tags.', verbose_name='Tags'),
        ),
        migrations.AlterUniqueTogether(
            name='fare',
            unique_together=set([('conference', 'code')]),
        ),
        migrations.AddField(
            model_name='eventtrack',
            name='track',
            field=models.ForeignKey(to='conference.Track'),
        ),
        migrations.AddField(
            model_name='eventinterest',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='eventbooking',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='event',
            name='schedule',
            field=models.ForeignKey(to='conference.Schedule'),
        ),
        migrations.AddField(
            model_name='event',
            name='sponsor',
            field=models.ForeignKey(blank=True, to='conference.Sponsor', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='talk',
            field=models.ForeignKey(blank=True, to='conference.Talk', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='tracks',
            field=models.ManyToManyField(to='conference.Track', through='conference.EventTrack'),
        ),
        migrations.AddField(
            model_name='attendeelink',
            name='attendee1',
            field=models.ForeignKey(related_name='link1', to='conference.AttendeeProfile'),
        ),
        migrations.AddField(
            model_name='attendeelink',
            name='attendee2',
            field=models.ForeignKey(related_name='link2', to='conference.AttendeeProfile'),
        ),
        migrations.AlterUniqueTogether(
            name='vototalk',
            unique_together=set([('user', 'talk')]),
        ),
        migrations.AlterUniqueTogether(
            name='talkspeaker',
            unique_together=set([('talk', 'speaker')]),
        ),
        migrations.AlterUniqueTogether(
            name='presence',
            unique_together=set([('profile', 'conference')]),
        ),
        migrations.AlterUniqueTogether(
            name='eventtrack',
            unique_together=set([('track', 'event')]),
        ),
        migrations.AlterUniqueTogether(
            name='eventinterest',
            unique_together=set([('user', 'event')]),
        ),
        migrations.AlterUniqueTogether(
            name='eventbooking',
            unique_together=set([('user', 'event')]),
        ),
    ]
