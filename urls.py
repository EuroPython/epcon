from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()


import pages.urls

urlpatterns = patterns('',
    #(r'^$', 'p3.views.root'),
    (r'^pycon3/assopy/$', 'conference.views.genro_wrapper'),
    (r'^pycon3/gmap.js$', 'p3.views.gmap'),
    #(r'^pycon3/__assopy-dev/$', 'conference.views.genro_wrapper'),
    (r'^admin/(.*)', admin.site.root),
    (r'^blog/', include('microblog.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),
    #(r'^pycon3/', include('pages.urls')),
    (r'^conference/', include('conference.urls')),
)

if settings.DEBUG:
    import os.path
    args = []
    for k, path in settings.STATIC_DIRS.items():
        args.append((
            r'^static/%s/(?P<path>.*)$' % k,
            'django.views.static.serve',
            {'document_root': os.path.join(path, k), 'show_indexes': True}
        ))
    urlpatterns += patterns('', *args)

urlpatterns += patterns('', (r'', include('pages.urls')))
