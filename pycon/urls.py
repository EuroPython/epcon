from django.conf import settings
from django.conf.urls import (
    include,
    url,
)
from django.contrib import admin
from django.views import (
    defaults,
    static,
)
from django.views.generic import RedirectView
from filebrowser.sites import site as fsite

import p3.forms as pforms
<<<<<<< HEAD
from conference.debug_panel import (
    debug_panel_index,
    debug_panel_invoice_placeholders,
    debug_panel_invoice_force_preview,
    debug_panel_invoice_export_for_tax_report_2018,
    debug_panel_invoice_export_for_tax_report_2018_csv,
    debug_panel_invoice_export_for_payment_reconciliation_json,
    reissue_invoice,
=======
from conference import views as conference_views
from conference.accounts import urlpatterns as accounts_urls
from conference.cart import urlpatterns_ep19 as cart19_urls
from conference.cfp import urlpatterns as cfp_urls
from conference.debug_panel import urlpatterns as debugpanel_urls
from conference.homepage import (
    generic_content_page,
    generic_content_page_with_sidebar,
    homepage,
>>>>>>> fbe11d2250baeca477a299ff135a1827ec1b9880
)
from conference.news import news_list
from conference.talk_voting import urlpatterns as talk_voting_urls
from conference.user_panel import urlpatterns as user_panel_urls
from conference.talks import urlpatterns as talks_urls
from conference.profiles import urlpatterns as profiles_urls
from conference.schedule import urlpatterns as schedule_urls

admin.autodiscover()
admin.site.index_template = 'p3/admin/index.html'

urlpatterns = [
    url(r'^$', homepage, name='homepage'),
    url(r'^generic-content-page/$', generic_content_page),
    url(r'^generic-content-page/with-sidebar/$', generic_content_page_with_sidebar),
    url(r'^user-panel/', include(user_panel_urls, namespace="user_panel")),
    url(r'^accounts/', include(accounts_urls, namespace="accounts")),
    url(r'^cfp/', include(cfp_urls, namespace="cfp")),
    url(r'^talks/', include(talks_urls, namespace="talks")),
    url(r'^profiles/', include(profiles_urls, namespace="profiles")),
    url(r'^talk-voting/', include(talk_voting_urls, namespace="talk_voting")),
    url(r'^schedule/', include(schedule_urls, namespace="schedule")),
    url(r'^news/', news_list, name="news"),
    url(r'^accounts/', include('assopy.urls')),
    url(r'^admin/filebrowser/', include(fsite.urls)),
    url(r'^admin/rosetta/', include('rosetta.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^cart/', include(cart19_urls, namespace="cart")),
    url(r'^p3/', include('p3.urls')),
    url(r'^conference/', include('conference.urls')),
    url(r'^conference/talks/(?P<slug>[\w-]+)$', conference_views.talk, name='conference-talk'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^markitup/', include('markitup.urls')),

    url('', include('social.apps.django_app.urls', namespace='social')),
    # TODO umgelurgel: See if the django.auth.urls are used anywhere and if they can be removed
    url(r'^login/', RedirectView.as_view(pattern_name='auth:login', permanent=False)),
    url('', include('django.contrib.auth.urls', namespace='auth')),

    # production debug panel, doesn't even have a name=
<<<<<<< HEAD
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
=======
    url(r'^nothing-to-see-here/', include(debugpanel_urls)),
>>>>>>> fbe11d2250baeca477a299ff135a1827ec1b9880
]

if settings.DEBUG:
    urlpatterns += [
        url(
            r"^media/(?P<path>.*)$",
            static.serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
        url(
            r"^500/$", defaults.server_error, kwargs={"exception": Exception()}
        ),
        url(
            r"^404/$",
            defaults.page_not_found,
            kwargs={"exception": Exception()},
        ),
        url(
            r"^403/$",
            defaults.permission_denied,
            kwargs={"exception": Exception()},
        ),
        url(
            r"^400/$", defaults.bad_request, kwargs={"exception": Exception()}
        ),
    ]

urlpatterns += [
    url(r'^', include('cms.urls')),
]

if hasattr(settings, 'ROSETTA_AFTER_SAVE'):
    # XXX this code would be better in settings.py, unfortunately there
    # it's impossible to import rosetta.signals because of a circular
    # dependency problem. urls.py is not the perfect place, but should
    # work always (with the exception of management commands).
    import rosetta.signals

    def on_rosetta_post_save(sender, **kw):
        settings.ROSETTA_AFTER_SAVE(sender=sender, **kw)
    rosetta.signals.post_save.connect(on_rosetta_post_save)
