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
# This view reimplements the old support of pages for ajax requests.
# If a request is ajax there is an ad-ho template to handle it.
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

