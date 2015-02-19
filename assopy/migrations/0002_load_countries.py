# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Don't use "from appname.models import ModelName".
        # Use orm.ModelName to refer to models in this application,
        # and orm['appname.ModelName'] for models in other applications.
        from django.core.management import call_command
        call_command("loaddata", "assopy/migrations/countries.json")

    def backwards(self, orm):
        "Write your backwards methods here."

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
        u'assopy.coupon': {
            'Meta': {'object_name': 'Coupon'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'conference': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Conference']"}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'end_validity': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'fares': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['conference.Fare']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'items_per_usage': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'max_usage': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'start_validity': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.User']", 'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '6'})
        },
        u'assopy.creditnote': {
            'Meta': {'object_name': 'CreditNote'},
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'null': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'emit_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'credit_notes'", 'to': u"orm['assopy.Invoice']"}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'})
        },
        u'assopy.invoice': {
            'Meta': {'object_name': 'Invoice'},
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '20', 'unique': 'True', 'null': 'True'}),
            'emit_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'invoices'", 'to': u"orm['assopy.Order']"}),
            'payment_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'vat': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Vat']"})
        },
        u'assopy.invoicelog': {
            'Meta': {'object_name': 'InvoiceLog'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Invoice']", 'null': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Order']", 'null': 'True'})
        },
        u'assopy.order': {
            'Meta': {'object_name': 'Order'},
            '_complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'address': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'assopy_id': ('django.db.models.fields.CharField', [], {'max_length': '22', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'billing_notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'card_name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'cf_code': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True'}),
            'country': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Country']", 'null': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'payment_url': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'orders'", 'to': u"orm['assopy.User']"}),
            'vat_number': ('django.db.models.fields.CharField', [], {'max_length': '22', 'blank': 'True'})
        },
        u'assopy.orderitem': {
            'Meta': {'object_name': 'OrderItem'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Order']"}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'ticket': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['conference.Ticket']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'vat': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Vat']"})
        },
        u'assopy.refund': {
            'Meta': {'object_name': 'Refund'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'credit_note': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['assopy.CreditNote']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'done': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'internal_note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Invoice']", 'null': 'True'}),
            'items': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['assopy.OrderItem']", 'through': u"orm['assopy.RefundOrderItem']", 'symmetrical': 'False'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'reject_reason': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '8'})
        },
        u'assopy.refundorderitem': {
            'Meta': {'unique_together': "(('orderitem', 'refund'),)", 'object_name': 'RefundOrderItem'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'orderitem': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.OrderItem']"}),
            'refund': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Refund']"})
        },
        u'assopy.token': {
            'Meta': {'object_name': 'Token'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'ctype': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'payload': ('django.db.models.fields.TextField', [], {'blank': "''"}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '36', 'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'})
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
        u'assopy.useridentity': {
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
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'identities'", 'to': u"orm['assopy.User']"})
        },
        u'assopy.useroauthinfo': {
            'Meta': {'object_name': 'UserOAuthInfo'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'service': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'token': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'oauth_infos'", 'to': u"orm['assopy.User']"})
        },
        u'assopy.vat': {
            'Meta': {'object_name': 'Vat'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '125', 'null': 'True', 'blank': 'True'}),
            'fares': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['conference.Fare']", 'null': 'True', 'through': u"orm['assopy.VatFare']", 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_notice': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.DecimalField', [], {'max_digits': '2', 'decimal_places': '0'})
        },
        u'assopy.vatfare': {
            'Meta': {'unique_together': "(('fare', 'vat'),)", 'object_name': 'VatFare'},
            'fare': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['conference.Fare']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'vat': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['assopy.Vat']"})
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
        }
    }

    complete_apps = ['assopy']
    symmetrical = True
