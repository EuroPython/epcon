# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'AttendeeProfile.assigned_to'
        db.add_column('p3_attendeeprofile', 'assigned_to', self.gf('django.db.models.fields.EmailField')(default='', max_length=75, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'AttendeeProfile.assigned_to'
        db.delete_column('p3_attendeeprofile', 'assigned_to')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'conference.attendee': {
            'Meta': {'object_name': 'Attendee'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'ticket': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conference.Ticket']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'conference.ticket': {
            'Meta': {'ordering': "('conference', 'code')", 'unique_together': "(('conference', 'code'),)", 'object_name': 'Ticket'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'end_validity': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'personal': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'start_validity': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'conference'", 'max_length': '10'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'p3.attendeeprofile': {
            'Meta': {'object_name': 'AttendeeProfile'},
            'assigned_to': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'attendee': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'p3_conference'", 'unique': 'True', 'to': "orm['conference.Attendee']"}),
            'diet': ('django.db.models.fields.CharField', [], {'default': "'omnivorous'", 'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'python_experience': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'shirt_size': ('django.db.models.fields.CharField', [], {'default': "'l'", 'max_length': '2'}),
            'tagline': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'})
        }
    }

    complete_apps = ['p3']
