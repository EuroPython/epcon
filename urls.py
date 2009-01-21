from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

from pages.urls import urlpatterns

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),
    (r'^blog/', include('microblog.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),
) + urlpatterns

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^static/stuff/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.P3_STUFF_DIR, 'show_indexes': True}
        ),
        (r'^static/p3/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.P3_STATIC_DIR, 'show_indexes': True}
        ),
    )
    urlpatterns += patterns('',
#        # Trick for Django to support static files (security hole: only for Dev environement! remove this on Prod!!!)
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
#        #url(r'^admin_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.ADMIN_MEDIA_ROOT}),
    )
