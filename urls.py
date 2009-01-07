from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    ('^$', 'p3.views.root'),
    (r'^admin/(.*)', admin.site.root),
)
if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/p3/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.P3_STATIC_DIR, 'show_indexes': True}
        ),
    )
