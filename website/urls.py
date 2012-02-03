# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

#import search_sites

admin.site.index_template = 'p3/admin/index.html'

from p3.forms import P3SubmissionForm, P3SubmissionAdditionalForm, P3TalkForm

urlpatterns = patterns('',
    (r'^accounts/', include('assopy.urls')),
    (r'^admin/filebrowser/', include('filebrowser.urls')),
    (r'^admin/rosetta/', include('rosetta.urls')),
    (r'^admin/templatesadmin/', include('templatesadmin.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^blog/', include('microblog.urls')),
    (r'^comments/', include('django.contrib.comments.urls')),
    url(r'^conference/paper-submission/$', 'conference.views.paper_submission', {'submission_form': P3SubmissionForm, 'submission_additional_form': P3SubmissionAdditionalForm, }, name='conference-paper-submission'),
    url(r'^conference/talks/(?P<slug>[\w-]+)$', 'conference.views.talk', {'talk_form': P3TalkForm}, name='conference-talk'),
    (r'^conference/', include('conference.urls')),
    (r'^hcomments/', include('hcomments.urls')),
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^p3/', include('p3.urls')),
#    (r'^search/', include('haystack.urls')),
)

#if settings.DEBUG:
#    import os.path
#    args = []
#    for k, path in settings.STATIC_DIRS.items():
#        args.append((
#            r'^static/%s/(?P<path>.*)$' % k,
#            'django.views.static.serve',
#            {'document_root': os.path.join(path, k), 'show_indexes': True}
#        ))
#    args.append((
#        r'^%s(?P<path>.*)$' % settings.MEDIA_URL[1:],
#        'django.views.static.serve',
#        {'document_root': settings.MEDIA_ROOT, 'show_indexes': True}
#    ))
#    from conference.settings import STUFF_URL, STUFF_DIR
#    args.append((
#        r'^%s(?P<path>.*)$' % STUFF_URL[1:],
#        'django.views.static.serve',
#        {'document_root': STUFF_DIR, 'show_indexes': True}
#    ))
#    urlpatterns += patterns('', *args)

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
