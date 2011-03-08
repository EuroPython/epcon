# -*- coding: UTF-8 -*-
from django.contrib import admin
from email_template import models

class EmailAdmin(admin.ModelAdmin):
    list_display = ( 'code', 'subject', 'from_email', 'cc', 'bcc' )

admin.site.register(models.Email, EmailAdmin)
