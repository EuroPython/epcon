# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.views import defaults

from filebrowser.sites import site as fsite

import p3.forms as pforms
from conference.debug_panel import (
    debug_panel_index,
    debug_panel_invoice_placeholders,
    debug_panel_invoice_force_preview,
    debug_panel_invoice_export_for_tax_report_2018,
    debug_panel_invoice_export_for_tax_report_2018_csv,
    debug_panel_invoice_export_for_payment_reconciliation_json,
    reissue_invoice,
)


admin.autodiscover()
admin.site.index_template = 'p3/admin/index.html'

urlpatterns = [
    url(r'^accounts/', include('assopy.urls')),
    url(r'^admin/filebrowser/', include(fsite.urls)),
    url(r'^admin/rosetta/', include('rosetta.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^comments/', include('django_comments.urls')),
    url(r'^p3/', include('p3.urls')),
    url(r'^conference/', include('conference.urls')),
    url(r'^conference/talks/(?P<slug>[\w-]+)$', 'conference.views.talk',
        {'talk_form': pforms.P3TalkForm},
        name='conference-talk'),
    url(r'^conference/speakers/(?P<slug>[\w-]+)', 'conference.views.speaker',
        {'speaker_form': pforms.P3SpeakerForm},
        name='conference-speaker'),
    url(r'^hcomments/', include('hcomments.urls')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^markitup/', include('markitup.urls')),


    url('', include('social.apps.django_app.urls', namespace='social')),
    url('', include('django.contrib.auth.urls', namespace='auth')),

    # production debug panel, doesn't even have a name=
    url(r'^nothing-to-see-here/$', debug_panel_index),
    url(r'^nothing-to-see-here/invoices/$',
        debug_panel_invoice_placeholders,
        name='debug_panel_invoice_placeholders'),
    url(r'^nothing-to-see-here/invoices/(?P<invoice_id>\d+)/$',
        debug_panel_invoice_force_preview,
        name="debug_panel_invoice_forcepreview"),
    url(r'^nothing-to-see-here/invoices_export/$',
        debug_panel_invoice_export_for_tax_report_2018,
        name='debug_panel_invoice_export_for_tax_report_2018'),
    url(r'^nothing-to-see-here/invoices_export.csv$',
        debug_panel_invoice_export_for_tax_report_2018_csv,
        name='debug_panel_invoice_export_for_tax_report_2018_csv'),
    url(r'^nothing-to-see-here/invoices_export_for_accounting.json$',
        debug_panel_invoice_export_for_payment_reconciliation_json,
        name='debug_panel_invoice_export_for_payment_reconciliation_json'),
    url(r'^nothing-to-see-here/invoices/reissue/(?P<invoice_id>\d+)/$',
        reissue_invoice,
        name='debug_panel_reissue_invoice'),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
        url(r'^500/$', defaults.server_error),
        url(r'^404/$', defaults.page_not_found),
        url(r'^403/$', defaults.permission_denied),
        url(r'^400/$', defaults.bad_request),
    ]

urlpatterns += i18n_patterns(
    '',
    url(r'^', include('cms.urls')),
)

if hasattr(settings, 'ROSETTA_AFTER_SAVE'):
    # XXX this code would be better in settings.py, unfortunately there
    # it's impossible to import rosetta.signals because of a circular
    # dependency problem. urls.py is not the perfect place, but should
    # work always (with the exception of management commands).
    import rosetta.signals

    def on_rosetta_post_save(sender, **kw):
        settings.ROSETTA_AFTER_SAVE(sender=sender, **kw)
    rosetta.signals.post_save.connect(on_rosetta_post_save)
