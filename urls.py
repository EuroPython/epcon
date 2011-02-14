from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/templatesadmin/', include('templatesadmin.urls')),
    (r'^admin/', include(admin.site.urls)),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='auth_logout'),
    (r'^assopy/$', 'conference.views.genro_wrapper'),
    (r'^p3/', include('p3.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^blog/', include('microblog.urls')),
    (r'^conference/', include('conference.urls')),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^hcomments/', include('hcomments.urls')),
    (r'^accounts/', include('assopy.urls')),
)

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^rosetta/', include('rosetta.urls')),
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
    args.append((
        r'^%s(?P<path>.*)$' % settings.MEDIA_URL[1:],
        'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}
    ))
    from conference.settings import STUFF_URL, STUFF_DIR
    args.append((
        r'^%s(?P<path>.*)$' % STUFF_URL[1:],
        'django.views.static.serve',
        {'document_root': STUFF_DIR, 'show_indexes': True}
    ))
    urlpatterns += patterns('', *args)

urlpatterns += patterns('', (r'', include('pages.urls')))
