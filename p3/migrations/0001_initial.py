# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'SpeakerConference'
        db.create_table(u'p3_speakerconference', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('speaker', self.gf('django.db.models.fields.related.OneToOneField')(related_name='p3_speaker', unique=True, to=orm['conference.Speaker'])),
            ('first_time', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'p3', ['SpeakerConference'])

        # Adding model 'TicketConference'
        db.create_table(u'p3_ticketconference', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ticket', self.gf('django.db.models.fields.related.OneToOneField')(related_name='p3_conference', unique=True, to=orm['conference.Ticket'])),
            ('shirt_size', self.gf('django.db.models.fields.CharField')(default='l', max_length=4)),
            ('python_experience', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('diet', self.gf('django.db.models.fields.CharField')(default='omnivorous', max_length=10)),
            ('tagline', self.gf('django.db.models.fields.CharField')(max_length=60, blank=True)),
            ('days', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('badge_image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
            ('assigned_to', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
        ))
        db.send_create_signal(u'p3', ['TicketConference'])

        # Adding model 'TicketSIM'
        db.create_table(u'p3_ticketsim', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ticket', self.gf('django.db.models.fields.related.OneToOneField')(related_name='p3_conference_sim', unique=True, to=orm['conference.Ticket'])),
            ('document', self.gf('django.db.models.fields.files.FileField')(max_length=100, blank=True)),
            ('sim_type', self.gf('django.db.models.fields.CharField')(default='std', max_length=5)),
            ('plan_type', self.gf('django.db.models.fields.CharField')(default='std', max_length=3)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=20, blank=True)),
        ))
        db.send_create_signal(u'p3', ['TicketSIM'])

        # Adding model 'HotelRoom'
        db.create_table(u'p3_hotelroom', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('conference', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Conference'])),
            ('room_type', self.gf('django.db.models.fields.CharField')(max_length=2)),
            ('quantity', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('amount', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'p3', ['HotelRoom'])

        # Adding unique constraint on 'HotelRoom', fields ['conference', 'room_type']
        db.create_unique(u'p3_hotelroom', ['conference_id', 'room_type'])

        # Adding model 'TicketRoom'
        db.create_table(u'p3_ticketroom', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ticket', self.gf('django.db.models.fields.related.OneToOneField')(related_name='p3_conference_room', unique=True, to=orm['conference.Ticket'])),
            ('document', self.gf('django.db.models.fields.files.FileField')(max_length=100, blank=True)),
            ('room_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['p3.HotelRoom'])),
            ('ticket_type', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('checkin', self.gf('django.db.models.fields.DateField')(db_index=True)),
            ('checkout', self.gf('django.db.models.fields.DateField')(db_index=True)),
            ('unused', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'p3', ['TicketRoom'])

        # Adding model 'Donation'
        db.create_table(u'p3_donation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.User'])),
            ('date', self.gf('django.db.models.fields.DateField')()),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=6, decimal_places=2)),
            ('message', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'p3', ['Donation'])

        # Adding model 'Sprint'
        db.create_table(u'p3_sprint', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.User'])),
            ('conference', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['conference.Conference'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('abstract', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'p3', ['Sprint'])

        # Adding model 'SprintPresence'
        db.create_table(u'p3_sprintpresence', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sprint', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['p3.Sprint'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['assopy.User'])),
        ))
        db.send_create_signal(u'p3', ['SprintPresence'])

        # Adding model 'P3Profile'
        db.create_table(u'p3_p3profile', (
            ('profile', self.gf('django.db.models.fields.related.OneToOneField')(related_name='p3_profile', unique=True, primary_key=True, to=orm['conference.AttendeeProfile'])),
            ('tagline', self.gf('django.db.models.fields.CharField')(max_length=60, blank=True)),
            ('twitter', self.gf('django.db.models.fields.CharField')(max_length=80, blank=True)),
            ('image_gravatar', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('image_url', self.gf('django.db.models.fields.URLField')(max_length=500)),
            ('country', self.gf('django.db.models.fields.CharField')(default='', max_length=2, db_index=True, blank=True)),
            ('spam_recruiting', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('spam_user_message', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('spam_sms', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'p3', ['P3Profile'])


    def backwards(self, orm):
        # Removing unique constraint on 'HotelRoom', fields ['conference', 'room_type']
        db.delete_unique(u'p3_hotelroom', ['conference_id', 'room_type'])

        # Deleting model 'SpeakerConference'
        db.delete_table(u'p3_speakerconference')

        # Deleting model 'TicketConference'
        db.delete_table(u'p3_ticketconference')

        # Deleting model 'TicketSIM'
        db.delete_table(u'p3_ticketsim')

        # Deleting model 'HotelRoom'
        db.delete_table(u'p3_hotelroom')

        # Deleting model 'TicketRoom'
        db.delete_table(u'p3_ticketroom')

        # Deleting model 'Donation'
        db.delete_table(u'p3_donation')

        # Deleting model 'Sprint'
        db.delete_table(u'p3_sprint')

        # Deleting model 'SprintPresence'
        db.delete_table(u'p3_sprintpresence')

        # Deleting model 'P3Profile'
        db.delete_table(u'p3_p3profile')


    models = {
        u'assopy.country': {
            'Meta': {'ordering': "['name']", 'object_name': 'Country'},
            'iso': ('django.db.models.fields.CharField', [], {'max_length': '2', 'primary_key': 'True'}),
            'iso3': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'numcode': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'printable_name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'vat_company': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'vat_company_verify': ('django.db.models.fields.CharField', [], {'default': "'-'", 'max_length': '1'}),
            'vat_person': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'assopy.user': {
            'Meta': {'object_name': 'User'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'unique': 'True', 'null': 'True'}),
            'card_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'cf_code': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Country']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'assopy_user'", 'unique': 'True', 'to': u"orm['auth.User']"}),
            'vat_number': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'})
        },
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
        u'conference.multilingualcontent': {
            'Meta': {'object_name': 'MultilingualContent'},
            'body': ('django.db.models.fields.TextField', [], {}),
            'content': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        u'conference.speaker': {
            'Meta': {'object_name': 'Speaker'},
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'p3.donation': {
            'Meta': {'object_name': 'Donation'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.User']"})
        },
        u'p3.hotelroom': {
            'Meta': {'unique_together': "(('conference', 'room_type'),)", 'object_name': 'HotelRoom'},
            'amount': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'conference': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Conference']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'quantity': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'room_type': ('django.db.models.fields.CharField', [], {'max_length': '2'})
        },
        u'p3.p3profile': {
            'Meta': {'object_name': 'P3Profile'},
            'country': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '2', 'db_index': 'True', 'blank': 'True'}),
            'image_gravatar': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'image_url': ('django.db.models.fields.URLField', [], {'max_length': '500'}),
            'profile': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'p3_profile'", 'unique': 'True', 'primary_key': 'True', 'to': u"orm['conference.AttendeeProfile']"}),
            'spam_recruiting': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'spam_sms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'spam_user_message': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'tagline': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'twitter': ('django.db.models.fields.CharField', [], {'max_length': '80', 'blank': 'True'})
        },
        u'p3.speakerconference': {
            'Meta': {'object_name': 'SpeakerConference'},
            'first_time': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'speaker': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'p3_speaker'", 'unique': 'True', 'to': u"orm['conference.Speaker']"})
        },
        u'p3.sprint': {
            'Meta': {'object_name': 'Sprint'},
            'abstract': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'conference': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Conference']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.User']"})
        },
        u'p3.sprintpresence': {
            'Meta': {'object_name': 'SprintPresence'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sprint': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['p3.Sprint']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.User']"})
        },
        u'p3.ticketconference': {
            'Meta': {'object_name': 'TicketConference'},
            'assigned_to': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'badge_image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'days': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'diet': ('django.db.models.fields.CharField', [], {'default': "'omnivorous'", 'max_length': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'python_experience': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'shirt_size': ('django.db.models.fields.CharField', [], {'default': "'l'", 'max_length': '4'}),
            'tagline': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ticket': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'p3_conference'", 'unique': 'True', 'to': u"orm['conference.Ticket']"})
        },
        u'p3.ticketroom': {
            'Meta': {'object_name': 'TicketRoom'},
            'checkin': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'checkout': ('django.db.models.fields.DateField', [], {'db_index': 'True'}),
            'document': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'room_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['p3.HotelRoom']"}),
            'ticket': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'p3_conference_room'", 'unique': 'True', 'to': u"orm['conference.Ticket']"}),
            'ticket_type': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'unused': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'p3.ticketsim': {
            'Meta': {'object_name': 'TicketSIM'},
            'document': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'plan_type': ('django.db.models.fields.CharField', [], {'default': "'std'", 'max_length': '3'}),
            'sim_type': ('django.db.models.fields.CharField', [], {'default': "'std'", 'max_length': '5'}),
            'ticket': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'p3_conference_sim'", 'unique': 'True', 'to': u"orm['conference.Ticket']"})
        }
    }

    complete_apps = ['p3']