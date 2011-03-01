# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Order.personal'
        db.add_column('assopy_order', 'personal', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)

        # Adding field 'Order.card_name'
        db.add_column('assopy_order', 'card_name', self.gf('django.db.models.fields.CharField')(default='', max_length=200), keep_default=False)

        # Adding field 'Order.vat_number'
        db.add_column('assopy_order', 'vat_number', self.gf('django.db.models.fields.CharField')(default='', max_length=22, blank=True), keep_default=False)

        # Adding field 'Order.tin_number'
        db.add_column('assopy_order', 'tin_number', self.gf('django.db.models.fields.CharField')(default='', max_length=16, blank=True), keep_default=False)

        # Adding field 'Order.country'
        db.add_column('assopy_order', 'country', self.gf('django.db.models.fields.related.ForeignKey')(default='IT', to=orm['assopy.Country']), keep_default=False)

        # Adding field 'Order.zip_code'
        db.add_column('assopy_order', 'zip_code', self.gf('django.db.models.fields.CharField')(default='', max_length=5, blank=True), keep_default=False)

        # Adding field 'Order.address'
        db.add_column('assopy_order', 'address', self.gf('django.db.models.fields.CharField')(default='', max_length=150, blank=True), keep_default=False)

        # Adding field 'Order.city'
        db.add_column('assopy_order', 'city', self.gf('django.db.models.fields.CharField')(default='', max_length=40, blank=True), keep_default=False)

        # Adding field 'Order.state'
        db.add_column('assopy_order', 'state', self.gf('django.db.models.fields.CharField')(default='', max_length=2, blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Order.personal'
        db.delete_column('assopy_order', 'personal')

        # Deleting field 'Order.card_name'
        db.delete_column('assopy_order', 'card_name')

        # Deleting field 'Order.vat_number'
        db.delete_column('assopy_order', 'vat_number')

        # Deleting field 'Order.tin_number'
        db.delete_column('assopy_order', 'tin_number')

        # Deleting field 'Order.country'
        db.delete_column('assopy_order', 'country_id')

        # Deleting field 'Order.zip_code'
        db.delete_column('assopy_order', 'zip_code')

        # Deleting field 'Order.address'
        db.delete_column('assopy_order', 'address')

        # Deleting field 'Order.city'
        db.delete_column('assopy_order', 'city')

        # Deleting field 'Order.state'
        db.delete_column('assopy_order', 'state')


    models = {
        'assopy.country': {
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
        'assopy.order': {
            'Meta': {'object_name': 'Order'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'unique': 'True', 'null': 'True'}),
            'card_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '8', 'null': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assopy.Country']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'payment_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'personal': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'tin_number': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assopy.User']"}),
            'vat_number': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'zip_code': ('django.db.models.fields.CharField', [], {'max_length': '5', 'blank': 'True'})
        },
        'assopy.orderitem': {
            'Meta': {'object_name': 'OrderItem'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assopy.Order']"}),
            'ticket': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['conference.Ticket']", 'unique': 'True'})
        },
        'assopy.token': {
            'Meta': {'object_name': 'Token'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'payload': ('django.db.models.fields.TextField', [], {'blank': "''"}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '36', 'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'})
        },
        'assopy.user': {
            'Meta': {'object_name': 'User'},
            'account_type': ('django.db.models.fields.CharField', [], {'default': "'p'", 'max_length': '1'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'unique': 'True', 'null': 'True'}),
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'card_name': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'cf_number': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['assopy.Country']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'jabber': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'photo': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'provincia': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'skype': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True'}),
            'twitter': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'assopy_user'", 'unique': 'True', 'to': "orm['auth.User']"}),
            'vat_number': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'}),
            'www': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'zip_code': ('django.db.models.fields.CharField', [], {'max_length': '5', 'blank': 'True'})
        },
        'assopy.useridentity': {
            'Meta': {'object_name': 'UserIdentity'},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'display_name': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'identifier': ('django.db.models.fields.CharField', [], {'max_length': '255', 'primary_key': 'True'}),
            'phoneNumber': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'photo': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'provider': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identities'", 'to': "orm['assopy.User']"})
        },
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
        'conference.fare': {
            'Meta': {'ordering': "('conference', 'code')", 'unique_together': "(('conference', 'code'),)", 'object_name': 'Fare'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'conference': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'end_validity': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'personal': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'start_validity': ('django.db.models.fields.DateField', [], {'null': 'True'}),
            'ticket_type': ('django.db.models.fields.CharField', [], {'default': "'conference'", 'max_length': '10'})
        },
        'conference.ticket': {
            'Meta': {'object_name': 'Ticket'},
            'fare': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['conference.Fare']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '60', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['assopy']
