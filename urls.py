from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^pycon3/assopy/$', 'conference.views.genro_wrapper'),
    (r'^pycon3/gmap.js$', 'p3.views.gmap'),
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^blog/', include('microblog.urls')),
    (r'^conference/', include('conference.urls')),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^hcomments/', include('hcomments.urls')),
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
    from conference.settings import CONFERENCE_STUFF_URL, CONFERENCE_STUFF_DIR
    args.append((
        r'^%s(?P<path>.*)$' % CONFERENCE_STUFF_URL[1:],
        'django.views.static.serve',
        {'document_root': CONFERENCE_STUFF_DIR, 'show_indexes': True}
    ))
    urlpatterns += patterns('', *args)

urlpatterns += patterns('', (r'', include('pages.urls')))
