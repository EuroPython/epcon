from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    ('^$', 'p3.views.root'),
    (r'^pycon3/', include('pages.urls')),
    (r'^admin/(.*)', admin.site.root),
)
if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/p3/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.P3_STATIC_DIR, 'show_indexes': True}
        ),
    )
    urlpatterns += patterns('',
#        # Trick for Django to support static files (security hole: only for Dev environement! remove this on Prod!!!)
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
#        #url(r'^admin_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ADMIN_MEDIA_ROOT}),
    )
