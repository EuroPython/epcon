# -*- coding: UTF-8 -*-
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.i18n import i18n_patterns

from django.contrib import admin
admin.autodiscover()

admin.site.index_template = 'p3/admin/index.html'

import p3.forms as pforms

from filebrowser.sites import site as fsite

urlpatterns = patterns('',
    (r'^accounts/', include('assopy.urls')),
    (r'^admin/filebrowser/', include(fsite.urls)),
    (r'^admin/rosetta/', include('rosetta.urls')),
    (r'^admin/templatesadmin/', include('templatesadmin.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^comments/', include('django.contrib.comments.urls')),
    url(r'^conference/talks/(?P<slug>[\w-]+)$', 'conference.views.talk',
        {'talk_form': pforms.P3TalkForm},
        name='conference-talk'),
    url(r'^conference/speakers/(?P<slug>[\w-]+)', 'conference.views.speaker',
        {'speaker_form': pforms.P3SpeakerForm},
        name='conference-speaker'),
    (r'^hcomments/', include('hcomments.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^markitup/', include('markitup.urls'))
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )

urlpatterns += i18n_patterns('',
    url(r'^', include('cms.urls')),
)

from django.conf import settings
if hasattr(settings, 'ROSETTA_AFTER_SAVE'):
    # XXX questo codice starebbe bene in settings.py, purtroppo li non posso
    # importare rosetta.signals (a causa di un problema di dipendenze
    # circolari). urls.py non è il posto perfetto ma dovrebbe funzionare sempre
    # (tranne che con i management command)
    import rosetta.signals
    def on_rosetta_post_save(sender, **kw):
        settings.ROSETTA_AFTER_SAVE(sender=sender, **kw)
    rosetta.signals.post_save.connect(on_rosetta_post_save)

