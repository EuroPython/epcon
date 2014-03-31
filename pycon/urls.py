# -*- coding: UTF-8 -*-
from django.conf import settings
from django.conf.urls import patterns, include, url

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
    (r'^blog/', include('microblog.urls')),
    (r'^comments/', include('django.contrib.comments.urls')),
    url(r'^conference/talks/(?P<slug>[\w-]+)$', 'conference.views.talk',
        {'talk_form': pforms.P3TalkForm},
        name='conference-talk'),
    url(r'^conference/speakers/(?P<slug>[\w-]+)', 'conference.views.speaker',
        {'speaker_form': pforms.P3SpeakerForm},
        name='conference-speaker'),
    (r'^conference/', include('conference.urls')),
    (r'^hcomments/', include('hcomments.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^p3/', include('p3.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )

from pages import views as pviews
# Questa view reimplementa il vecchio supporto di pages per le richieste ajax.
# Se una richiesta è ajax viene utilizzato un template ad hoc
class DetailsWithAjaxSupport(pviews.Details):
    def get_template(self, request, context):
        tpl = super(DetailsWithAjaxSupport, self).get_template(request, context)
        if request.is_ajax():
            import os.path
            bname, fname = os.path.split(tpl)
            tpl = os.path.join(bname, 'body_' + fname)
        return tpl
pviews.details = DetailsWithAjaxSupport()
urlpatterns += patterns('', (r'', include('pages.urls')))

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

from django import http
from django.conf import settings
from pages import managers
from pages import models

class MyPageManager(managers.PageManager):
    def from_path(self, complete_path, lang, exclude_drafts=True):
        output = super(MyPageManager, self).from_path(complete_path, lang, exclude_drafts)
        if output is None:
            # non esiste una pagina per il path richiesto nella lingua
            # specificata, ma forse esiste in un'altra lingua...
            for alternative_lang, _ in settings.PAGE_LANGUAGES:
                if alternative_lang != lang:
                    alt_content = super(MyPageManager, self).from_path(complete_path, alternative_lang, exclude_drafts)
                    if alt_content:
                        # ho trovato una pagina che coincide con
                        # `complete_path` ma nella lingua `alternative_lang`,
                        # faccio un redirect...
                        from pycon.middleware import RisingResponse
                        RisingResponse.stop(http.HttpResponseRedirect(alt_content.get_url_path(lang)))
        return output

models.Page.add_to_class('objects', MyPageManager())
