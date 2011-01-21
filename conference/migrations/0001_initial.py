# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Deadline'
        db.create_table('conference_deadline', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('conference', ['Deadline'])

        # Adding model 'DeadlineContent'
        db.create_table('conference_deadlinecontent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('deadline', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Deadline'])),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('body', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('conference', ['DeadlineContent'])

        # Adding model 'MultilingualContent'
        db.create_table('conference_multilingualcontent', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('content', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('body', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('conference', ['MultilingualContent'])

        # Adding model 'Speaker'
        db.create_table('conference_speaker', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('activity', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('industry', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('location', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('activity_homepage', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('twitter', self.gf('django.db.models.fields.CharField')(max_length=80, blank=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('conference', ['Speaker'])

        # Adding model 'Talk'
        db.create_table('conference_talk', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('duration', self.gf('django.db.models.fields.IntegerField')()),
            ('language', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('slides', self.gf('django.db.models.fields.files.FileField')(max_length=100, blank=True)),
            ('video_type', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('video_url', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('video_file', self.gf('django.db.models.fields.files.FileField')(max_length=100, blank=True)),
            ('tags', self.gf('tagging.fields.TagField')()),
        ))
        db.send_create_signal('conference', ['Talk'])

        # Adding M2M table for field speakers on 'Talk'
        db.create_table('conference_talk_speakers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('talk', models.ForeignKey(orm['conference.talk'], null=False)),
            ('speaker', models.ForeignKey(orm['conference.speaker'], null=False))
        ))
        db.create_unique('conference_talk_speakers', ['talk_id', 'speaker_id'])

        # Adding M2M table for field additional_speakers on 'Talk'
        db.create_table('conference_talk_additional_speakers', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('talk', models.ForeignKey(orm['conference.talk'], null=False)),
            ('speaker', models.ForeignKey(orm['conference.speaker'], null=False))
        ))
        db.create_unique('conference_talk_additional_speakers', ['talk_id', 'speaker_id'])

        # Adding model 'Sponsor'
        db.create_table('conference_sponsor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sponsor', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('logo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('conference', ['Sponsor'])

        # Adding model 'SponsorIncome'
        db.create_table('conference_sponsorincome', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sponsor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Sponsor'])),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('income', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('tags', self.gf('tagging.fields.TagField')()),
        ))
        db.send_create_signal('conference', ['SponsorIncome'])

        # Adding model 'MediaPartner'
        db.create_table('conference_mediapartner', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('partner', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
            ('logo', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('conference', ['MediaPartner'])

        # Adding model 'MediaPartnerConference'
        db.create_table('conference_mediapartnerconference', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('partner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.MediaPartner'])),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('tags', self.gf('tagging.fields.TagField')()),
        ))
        db.send_create_signal('conference', ['MediaPartnerConference'])

        # Adding model 'Schedule'
        db.create_table('conference_schedule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('conference', ['Schedule'])

        # Adding model 'Track'
        db.create_table('conference_track', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('schedule', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Schedule'])),
            ('track', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('title', self.gf('django.db.models.fields.TextField')()),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('translate', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('conference', ['Track'])

        # Adding model 'Event'
        db.create_table('conference_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('schedule', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Schedule'])),
            ('talk', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Talk'], null=True, blank=True)),
            ('custom', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('start_time', self.gf('django.db.models.fields.TimeField')()),
            ('track', self.gf('tagging.fields.TagField')()),
            ('sponsor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Sponsor'], null=True, blank=True)),
        ))
        db.send_create_signal('conference', ['Event'])

        # Adding model 'Hotel'
        db.create_table('conference_hotel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
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
        db.send_create_signal('conference', ['Hotel'])

        # Adding model 'DidYouKnow'
        db.create_table('conference_didyouknow', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('visible', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('conference', ['DidYouKnow'])

        # Adding model 'Quote'
        db.create_table('conference_quote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('who', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('conference', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('activity', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, blank=True)),
        ))
        db.send_create_signal('conference', ['Quote'])


    def backwards(self, orm):
        
        # Deleting model 'Deadline'
        db.delete_table('conference_deadline')

        # Deleting model 'DeadlineContent'
        db.delete_table('conference_deadlinecontent')

        # Deleting model 'MultilingualContent'
        db.delete_table('conference_multilingualcontent')

        # Deleting model 'Speaker'
        db.delete_table('conference_speaker')

        # Deleting model 'Talk'
        db.delete_table('conference_talk')

        # Removing M2M table for field speakers on 'Talk'
        db.delete_table('conference_talk_speakers')

        # Removing M2M table for field additional_speakers on 'Talk'
        db.delete_table('conference_talk_additional_speakers')

        # Deleting model 'Sponsor'
        db.delete_table('conference_sponsor')

        # Deleting model 'SponsorIncome'
        db.delete_table('conference_sponsorincome')

        # Deleting model 'MediaPartner'
        db.delete_table('conference_mediapartner')

        # Deleting model 'MediaPartnerConference'
        db.delete_table('conference_mediapartnerconference')

        # Deleting model 'Schedule'
        db.delete_table('conference_schedule')

        # Deleting model 'Track'
        db.delete_table('conference_track')

        # Deleting model 'Event'
        db.delete_table('conference_event')

        # Deleting model 'Hotel'
        db.delete_table('conference_hotel')

        # Deleting model 'DidYouKnow'
        db.delete_table('conference_didyouknow')

        # Deleting model 'Quote'
        db.delete_table('conference_quote')


    models = {
        'conference.deadline': {
            'Meta': {'ordering': "['date']", 'object_name': 'Deadline'},
            'date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'conference.deadlinecontent': {
            'Meta': {'object_name': 'DeadlineContent'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'deadline': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conference.Deadline']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '3'})
        },
        'conference.didyouknow': {
            'Meta': {'object_name': 'DidYouKnow'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'conference.event': {
            'Meta': {'ordering': "['start_time']", 'object_name': 'Event'},
            'custom': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'schedule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conference.Schedule']"}),
            'sponsor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conference.Sponsor']", 'null': 'True', 'blank': 'True'}),
            'start_time': ('django.db.models.fields.TimeField', [], {}),
            'talk': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conference.Talk']", 'null': 'True', 'blank': 'True'}),
            'track': ('tagging.fields.TagField', [], {})
        },
        'conference.hotel': {
            'Meta': {'ordering': "['name']", 'object_name': 'Hotel'},
            'address': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '200', 'blank': 'True'}),
            'affiliated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'availability': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
        'conference.mediapartner': {
            'Meta': {'ordering': "['partner']", 'object_name': 'MediaPartner'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'partner': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'conference.mediapartnerconference': {
            'Meta': {'ordering': "['conference']", 'object_name': 'MediaPartnerConference'},
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'partner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conference.MediaPartner']"}),
            'tags': ('tagging.fields.TagField', [], {})
        },
        'conference.multilingualcontent': {
            'Meta': {'object_name': 'MultilingualContent'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'conference.quote': {
            'Meta': {'ordering': "['conference', 'who']", 'object_name': 'Quote'},
            'activity': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'who': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'conference.schedule': {
            'Meta': {'object_name': 'Schedule'},
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'})
        },
        'conference.speaker': {
            'Meta': {'ordering': "['name']", 'object_name': 'Speaker'},
            'activity': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'activity_homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'industry': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'location': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'twitter': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        'conference.sponsor': {
            'Meta': {'ordering': "['sponsor']", 'object_name': 'Sponsor'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'logo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'sponsor': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'conference.sponsorincome': {
            'Meta': {'ordering': "['conference']", 'object_name': 'SponsorIncome'},
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'income': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'sponsor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conference.Sponsor']"}),
            'tags': ('tagging.fields.TagField', [], {})
        },
        'conference.talk': {
            'Meta': {'ordering': "['title']", 'object_name': 'Talk'},
            'additional_speakers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'additional_speakers'", 'blank': 'True', 'to': "orm['conference.Speaker']"}),
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'duration': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'slides': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'speakers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['conference.Speaker']", 'symmetrical': 'False'}),
            'tags': ('tagging.fields.TagField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'video_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            'video_type': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'video_url': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'conference.track': {
            'Meta': {'ordering': "['order']", 'object_name': 'Track'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'schedule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conference.Schedule']"}),
            'title': ('django.db.models.fields.TextField', [], {}),
            'track': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'translate': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['conference']
