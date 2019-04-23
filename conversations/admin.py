from django.contrib import admin

from .models import Thread, Message, Attachment


admin.site.register(Thread)
admin.site.register(Message)
admin.site.register(Attachment)
