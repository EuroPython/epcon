# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Talk.duration'
        db.add_column(u'conference_talk', 'duration',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Talk.duration'
        db.delete_column(u'conference_talk', 'duration')


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