# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ConferenceTag'
        db.create_table(u'conference_conferencetag', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=100)),
            ('category', self.gf('django.db.models.fields.CharField')(default='', max_length=50, blank=True)),
        ))
        db.send_create_signal(u'conference', ['ConferenceTag'])

        # Adding model 'ConferenceTaggedItem'
        db.create_table(u'conference_conferencetaggeditem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('object_id', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'conference_conferencetaggeditem_tagged_items', to=orm['contenttypes.ContentType'])),
            ('tag', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'conference_conferencetaggeditem_items', to=orm['conference.ConferenceTag'])),
        ))
        db.send_create_signal(u'conference', ['ConferenceTaggedItem'])

        # Adding model 'Conference'
        db.create_table(u'conference_conference', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10, primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('cfp_start', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('cfp_end', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('conference_start', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('conference_end', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('voting_start', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('voting_end', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'conference', ['Conference'])

        # Adding model 'Deadline'
        db.create_table(u'conference_deadline', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal(u'conference', ['Deadline'])

        # Adding model 'DeadlineContent'
        db.create_table(u'conference_deadlinecontent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('deadline', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Deadline'])),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('body', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'conference', ['DeadlineContent'])

        # Adding model 'MultilingualContent'
        db.create_table(u'conference_multilingualcontent', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('content', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('body', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'conference', ['MultilingualContent'])

        # Adding model 'AttendeeProfile'
        db.create_table(u'conference_attendeeprofile', (
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True, primary_key=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('uuid', self.gf('django.db.models.fields.CharField')(unique=True, max_length=6)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('birthday', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('personal_homepage', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('company', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('company_homepage', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('job_title', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('visibility', self.gf('django.db.models.fields.CharField')(default='x', max_length=1)),
        ))
        db.send_create_signal(u'conference', ['AttendeeProfile'])

        # Adding model 'Presence'
        db.create_table(u'conference_presence', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('profile', self.gf('django.db.models.fields.related.ForeignKey')(related_name='presences', to=orm['conference.AttendeeProfile'])),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'conference', ['Presence'])

        # Adding unique constraint on 'Presence', fields ['profile', 'conference']
        db.create_unique(u'conference_presence', ['profile_id', 'conference'])

        # Adding model 'AttendeeLink'
        db.create_table(u'conference_attendeelink', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('attendee1', self.gf('django.db.models.fields.related.ForeignKey')(related_name='link1', to=orm['conference.AttendeeProfile'])),
            ('attendee2', self.gf('django.db.models.fields.related.ForeignKey')(related_name='link2', to=orm['conference.AttendeeProfile'])),
            ('message', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'conference', ['AttendeeLink'])

        # Adding model 'Speaker'
        db.create_table(u'conference_speaker', (
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'conference', ['Speaker'])

        # Adding model 'Talk'
        db.create_table(u'conference_talk', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=80)),
            ('sub_title', self.gf('django.db.models.fields.CharField')(default='', max_length=1000, blank=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=100)),
            ('prerequisites', self.gf('django.db.models.fields.CharField')(default='', max_length=150, blank=True)),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('admin_type', self.gf('django.db.models.fields.CharField')(max_length=1, blank=True)),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('abstract_short', self.gf('django.db.models.fields.TextField')(default='')),
            ('abstract_extra', self.gf('django.db.models.fields.TextField')(default='')),
            ('slides', self.gf('django.db.models.fields.files.FileField')(max_length=100, blank=True)),
            ('video_type', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('video_url', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('video_file', self.gf('django.db.models.fields.files.FileField')(max_length=100, blank=True)),
            ('teaser_video', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('level', self.gf('django.db.models.fields.CharField')(default='beginner', max_length=12)),
            ('training_available', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('type', self.gf('django.db.models.fields.CharField')(default='t_30', max_length=5)),
            ('duration', self.gf('django.db.models.fields.IntegerField')()),
            ('suggested_tags', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'conference', ['Talk'])

        # Adding model 'TalkSpeaker'
        db.create_table(u'conference_talkspeaker', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('talk', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Talk'])),
            ('speaker', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Speaker'])),
            ('helper', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'conference', ['TalkSpeaker'])

        # Adding unique constraint on 'TalkSpeaker', fields ['talk', 'speaker']
        db.create_unique(u'conference_talkspeaker', ['talk_id', 'speaker_id'])

        # Adding model 'Fare'
        db.create_table(u'conference_fare', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=6, decimal_places=2)),
            ('start_validity', self.gf('django.db.models.fields.DateField')(null=True)),
            ('end_validity', self.gf('django.db.models.fields.DateField')(null=True)),
            ('recipient_type', self.gf('django.db.models.fields.CharField')(default='p', max_length=1)),
            ('ticket_type', self.gf('django.db.models.fields.CharField')(default='conference', max_length=10, db_index=True)),
            ('payment_type', self.gf('django.db.models.fields.CharField')(default='p', max_length=1)),
            ('blob', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'conference', ['Fare'])

        # Adding unique constraint on 'Fare', fields ['conference', 'code']
        db.create_unique(u'conference_fare', ['conference', 'code'])

        # Adding model 'Ticket'
        db.create_table(u'conference_ticket', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=60, blank=True)),
            ('fare', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Fare'])),
            ('frozen', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('ticket_type', self.gf('django.db.models.fields.CharField')(default='standard', max_length=8)),
        ))
        db.send_create_signal(u'conference', ['Ticket'])

        # Adding model 'Sponsor'
        db.create_table(u'conference_sponsor', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sponsor', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('logo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
            ('alt_text', self.gf('django.db.models.fields.CharField')(max_length=150, blank=True)),
            ('title_text', self.gf('django.db.models.fields.CharField')(max_length=150, blank=True)),
        ))
        db.send_create_signal(u'conference', ['Sponsor'])

        # Adding model 'SponsorIncome'
        db.create_table(u'conference_sponsorincome', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sponsor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Sponsor'])),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('income', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('tags', self.gf('tagging.fields.TagField')()),
        ))
        db.send_create_signal(u'conference', ['SponsorIncome'])

        # Adding model 'MediaPartner'
        db.create_table(u'conference_mediapartner', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('partner', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('logo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
        ))
        db.send_create_signal(u'conference', ['MediaPartner'])

        # Adding model 'MediaPartnerConference'
        db.create_table(u'conference_mediapartnerconference', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('partner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.MediaPartner'])),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('tags', self.gf('tagging.fields.TagField')()),
        ))
        db.send_create_signal(u'conference', ['MediaPartnerConference'])

        # Adding model 'Schedule'
        db.create_table(u'conference_schedule', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50)),
            ('date', self.gf('django.db.models.fields.DateField')()),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'conference', ['Schedule'])

        # Adding model 'Track'
        db.create_table(u'conference_track', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('schedule', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Schedule'])),
            ('track', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('title', self.gf('django.db.models.fields.TextField')()),
            ('seats', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('translate', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('outdoor', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'conference', ['Track'])

        # Adding model 'Event'
        db.create_table(u'conference_event', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('schedule', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Schedule'])),
            ('start_time', self.gf('django.db.models.fields.TimeField')()),
            ('talk', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Talk'], null=True, blank=True)),
            ('custom', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('abstract', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('duration', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('tags', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('sponsor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Sponsor'], null=True, blank=True)),
            ('video', self.gf('django.db.models.fields.CharField')(max_length=1000, blank=True)),
            ('bookable', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('seats', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal(u'conference', ['Event'])

        # Adding model 'EventTrack'
        db.create_table(u'conference_eventtrack', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('track', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Track'])),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Event'])),
        ))
        db.send_create_signal(u'conference', ['EventTrack'])

        # Adding unique constraint on 'EventTrack', fields ['track', 'event']
        db.create_unique(u'conference_eventtrack', ['track_id', 'event_id'])

        # Adding model 'EventInterest'
        db.create_table(u'conference_eventinterest', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Event'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('interest', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'conference', ['EventInterest'])

        # Adding unique constraint on 'EventInterest', fields ['user', 'event']
        db.create_unique(u'conference_eventinterest', ['user_id', 'event_id'])

        # Adding model 'EventBooking'
        db.create_table(u'conference_eventbooking', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Event'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal(u'conference', ['EventBooking'])

        # Adding unique constraint on 'EventBooking', fields ['user', 'event']
        db.create_unique(u'conference_eventbooking', ['user_id', 'event_id'])

        # Adding model 'Hotel'
        db.create_table(u'conference_hotel', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('telephone', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('availability', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('price', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('note', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('affiliated', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('visible', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('address', self.gf('django.db.models.fields.CharField')(default='', max_length=200, blank=True)),
            ('lng', self.gf('django.db.models.fields.FloatField')(default=0.0, blank=True)),
            ('lat', self.gf('django.db.models.fields.FloatField')(default=0.0, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'conference', ['Hotel'])

        # Adding model 'SpecialPlace'
        db.create_table(u'conference_specialplace', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('address', self.gf('django.db.models.fields.CharField')(default='', max_length=200, blank=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('telephone', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('note', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('visible', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('lng', self.gf('django.db.models.fields.FloatField')(default=0.0, blank=True)),
            ('lat', self.gf('django.db.models.fields.FloatField')(default=0.0, blank=True)),
        ))
        db.send_create_signal(u'conference', ['SpecialPlace'])

        # Adding model 'DidYouKnow'
        db.create_table(u'conference_didyouknow', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('visible', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'conference', ['DidYouKnow'])

        # Adding model 'Quote'
        db.create_table(u'conference_quote', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('who', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('activity', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
        ))
        db.send_create_signal(u'conference', ['Quote'])

        # Adding model 'VotoTalk'
        db.create_table(u'conference_vototalk', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('talk', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Talk'])),
            ('vote', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=2)),
        ))
        db.send_create_signal(u'conference', ['VotoTalk'])

        # Adding unique constraint on 'VotoTalk', fields ['user', 'talk']
        db.create_unique(u'conference_vototalk', ['user_id', 'talk_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'VotoTalk', fields ['user', 'talk']
        db.delete_unique(u'conference_vototalk', ['user_id', 'talk_id'])

        # Removing unique constraint on 'EventBooking', fields ['user', 'event']
        db.delete_unique(u'conference_eventbooking', ['user_id', 'event_id'])

        # Removing unique constraint on 'EventInterest', fields ['user', 'event']
        db.delete_unique(u'conference_eventinterest', ['user_id', 'event_id'])

        # Removing unique constraint on 'EventTrack', fields ['track', 'event']
        db.delete_unique(u'conference_eventtrack', ['track_id', 'event_id'])

        # Removing unique constraint on 'Fare', fields ['conference', 'code']
        db.delete_unique(u'conference_fare', ['conference', 'code'])

        # Removing unique constraint on 'TalkSpeaker', fields ['talk', 'speaker']
        db.delete_unique(u'conference_talkspeaker', ['talk_id', 'speaker_id'])

        # Removing unique constraint on 'Presence', fields ['profile', 'conference']
        db.delete_unique(u'conference_presence', ['profile_id', 'conference'])

        # Deleting model 'ConferenceTag'
        db.delete_table(u'conference_conferencetag')

        # Deleting model 'ConferenceTaggedItem'
        db.delete_table(u'conference_conferencetaggeditem')

        # Deleting model 'Conference'
        db.delete_table(u'conference_conference')

        # Deleting model 'Deadline'
        db.delete_table(u'conference_deadline')

        # Deleting model 'DeadlineContent'
        db.delete_table(u'conference_deadlinecontent')

        # Deleting model 'MultilingualContent'
        db.delete_table(u'conference_multilingualcontent')

        # Deleting model 'AttendeeProfile'
        db.delete_table(u'conference_attendeeprofile')

        # Deleting model 'Presence'
        db.delete_table(u'conference_presence')

        # Deleting model 'AttendeeLink'
        db.delete_table(u'conference_attendeelink')

        # Deleting model 'Speaker'
        db.delete_table(u'conference_speaker')

        # Deleting model 'Talk'
        db.delete_table(u'conference_talk')

        # Deleting model 'TalkSpeaker'
        db.delete_table(u'conference_talkspeaker')

        # Deleting model 'Fare'
        db.delete_table(u'conference_fare')

        # Deleting model 'Ticket'
        db.delete_table(u'conference_ticket')

        # Deleting model 'Sponsor'
        db.delete_table(u'conference_sponsor')

        # Deleting model 'SponsorIncome'
        db.delete_table(u'conference_sponsorincome')

        # Deleting model 'MediaPartner'
        db.delete_table(u'conference_mediapartner')

        # Deleting model 'MediaPartnerConference'
        db.delete_table(u'conference_mediapartnerconference')

        # Deleting model 'Schedule'
        db.delete_table(u'conference_schedule')

        # Deleting model 'Track'
        db.delete_table(u'conference_track')

        # Deleting model 'Event'
        db.delete_table(u'conference_event')

        # Deleting model 'EventTrack'
        db.delete_table(u'conference_eventtrack')

        # Deleting model 'EventInterest'
        db.delete_table(u'conference_eventinterest')

        # Deleting model 'EventBooking'
        db.delete_table(u'conference_eventbooking')

        # Deleting model 'Hotel'
        db.delete_table(u'conference_hotel')

        # Deleting model 'SpecialPlace'
        db.delete_table(u'conference_specialplace')

        # Deleting model 'DidYouKnow'
        db.delete_table(u'conference_didyouknow')

        # Deleting model 'Quote'
        db.delete_table(u'conference_quote')

        # Deleting model 'VotoTalk'
        db.delete_table(u'conference_vototalk')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'conference.attendeelink': {
            'Meta': {'object_name': 'AttendeeLink'},
            'attendee1': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'link1'", 'to': u"orm['conference.AttendeeProfile']"}),
            'attendee2': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'link2'", 'to': u"orm['conference.AttendeeProfile']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        u'conference.attendeeprofile': {
            'Meta': {'object_name': 'AttendeeProfile'},
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'company': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'company_homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'job_title': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'personal_homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'uuid': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '6'}),
            'visibility': ('django.db.models.fields.CharField', [], {'default': "'x'", 'max_length': '1'})
        },
        u'conference.conference': {
            'Meta': {'object_name': 'Conference'},
            'cfp_end': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'cfp_start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10', 'primary_key': 'True'}),
            'conference_end': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'conference_start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'voting_end': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'voting_start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'})
        },
        u'conference.conferencetag': {
            'Meta': {'object_name': 'ConferenceTag'},
            'category': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'conference.conferencetaggeditem': {
            'Meta': {'object_name': 'ConferenceTaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'conference_conferencetaggeditem_tagged_items'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'conference_conferencetaggeditem_items'", 'to': u"orm['conference.ConferenceTag']"})
        },
        u'conference.deadline': {
            'Meta': {'ordering': "['date']", 'object_name': 'Deadline'},
            'date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'conference.deadlinecontent': {
            'Meta': {'object_name': 'DeadlineContent'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'deadline': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Deadline']"}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        u'conference.didyouknow': {
            'Meta': {'object_name': 'DidYouKnow'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'conference.event': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Event'},
            'abstract': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'bookable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'custom': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'schedule': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Schedule']"}),
            'seats': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'sponsor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Sponsor']", 'null': 'True', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.TimeField', [], {}),
            'tags': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'talk': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Talk']", 'null': 'True', 'blank': 'True'}),
            'tracks': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['conference.Track']", 'through': u"orm['conference.EventTrack']", 'symmetrical': 'False'}),
            'video': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'})
        },
        u'conference.eventbooking': {
            'Meta': {'unique_together': "(('user', 'event'),)", 'object_name': 'EventBooking'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'conference.eventinterest': {
            'Meta': {'unique_together': "(('user', 'event'),)", 'object_name': 'EventInterest'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interest': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'conference.eventtrack': {
            'Meta': {'unique_together': "(('track', 'event'),)", 'object_name': 'EventTrack'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'track': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Track']"})
        },
        u'conference.fare': {
            'Meta': {'unique_together': "(('conference', 'code'),)", 'object_name': 'Fare'},
            'blob': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'end_validity': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'payment_type': ('django.db.models.fields.CharField', [], {'default': "'p'", 'max_length': '1'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'recipient_type': ('django.db.models.fields.CharField', [], {'default': "'p'", 'max_length': '1'}),
            'start_validity': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'ticket_type': ('django.db.models.fields.CharField', [], {'default': "'conference'", 'max_length': '10', 'db_index': 'True'})
        },
        u'conference.hotel': {
            'Meta': {'ordering': "['name']", 'object_name': 'Hotel'},
            'address': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'affiliated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'availability': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'blank': 'True'}),
            'lng': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'blank': 'True'}),
            'modified': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'price': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'telephone': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'conference.mediapartner': {
            'Meta': {'ordering': "['partner']", 'object_name': 'MediaPartner'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'partner': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        u'conference.mediapartnerconference': {
            'Meta': {'ordering': "['conference']", 'object_name': 'MediaPartnerConference'},
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'partner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.MediaPartner']"}),
            'tags': ('tagging.fields.TagField', [], {})
        },
        u'conference.multilingualcontent': {
            'Meta': {'object_name': 'MultilingualContent'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        u'conference.presence': {
            'Meta': {'unique_together': "(('profile', 'conference'),)", 'object_name': 'Presence'},
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'presences'", 'to': u"orm['conference.AttendeeProfile']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        u'conference.quote': {
            'Meta': {'ordering': "['conference', 'who']", 'object_name': 'Quote'},
            'activity': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'who': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'conference.schedule': {
            'Meta': {'ordering': "['date']", 'object_name': 'Schedule'},
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'})
        },
        u'conference.speaker': {
            'Meta': {'object_name': 'Speaker'},
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'conference.specialplace': {
            'Meta': {'ordering': "['name']", 'object_name': 'SpecialPlace'},
            'address': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'blank': 'True'}),
            'lng': ('django.db.models.fields.FloatField', [], {'default': '0.0', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'telephone': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        u'conference.sponsor': {
            'Meta': {'ordering': "['sponsor']", 'object_name': 'Sponsor'},
            'alt_text': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'sponsor': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'title_text': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        u'conference.sponsorincome': {
            'Meta': {'ordering': "['conference']", 'object_name': 'SponsorIncome'},
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'income': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'sponsor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Sponsor']"}),
            'tags': ('tagging.fields.TagField', [], {})
        },
        u'conference.talk': {
            'Meta': {'ordering': "['title']", 'object_name': 'Talk'},
            'abstract_extra': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'abstract_short': ('django.db.models.fields.TextField', [], {'default': "''"}),
            'admin_type': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'duration': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'level': ('django.db.models.fields.CharField', [], {'default': "'beginner'", 'max_length': '12'}),
            'prerequisites': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '150', 'blank': 'True'}),
            'slides': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['conference.Speaker']", 'through': u"orm['conference.TalkSpeaker']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'sub_title': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1000', 'blank': 'True'}),
            'suggested_tags': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'teaser_video': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'training_available': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'t_30'", 'max_length': '5'}),
            'video_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'video_type': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'video_url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'conference.talkspeaker': {
            'Meta': {'unique_together': "(('talk', 'speaker'),)", 'object_name': 'TalkSpeaker'},
            'helper': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'speaker': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Speaker']"}),
            'talk': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Talk']"})
        },
        u'conference.ticket': {
            'Meta': {'object_name': 'Ticket'},
            'fare': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Fare']"}),
            'frozen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ticket_type': ('django.db.models.fields.CharField', [], {'default': "'standard'", 'max_length': '8'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'conference.track': {
            'Meta': {'object_name': 'Track'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'outdoor': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'schedule': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Schedule']"}),
            'seats': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'track': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'translate': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'conference.vototalk': {
            'Meta': {'unique_together': "(('user', 'talk'),)", 'object_name': 'VotoTalk'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'talk': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Talk']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'vote': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['conference']