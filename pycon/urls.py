# -*- coding: utf-8 -*-

from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views import defaults, static
from django.views.generic import RedirectView

from filebrowser.sites import site as fsite

import p3.forms as pforms
from conference import views as conference_views
from conference.accounts import urlpatterns as accounts_urls
from conference.debug_panel import urlpatterns as debugpanel_urls
from conference.homepage import (
    form_testing,
    generic_content_page,
    generic_content_page_with_sidebar,
    homepage,
)
from conference.user_panel import urlpatterns as user_panel_urls
from conference.cfp import urlpatterns as cfp_urls
from conference.news import news_list


admin.autodiscover()
admin.site.index_template = 'p3/admin/index.html'

urlpatterns = [
    url(r'^$', homepage, name='homepage'),
    url(r'^generic-content-page/$', generic_content_page),
    url(r'^generic-content-page/with-sidebar/$',
        generic_content_page_with_sidebar),
    url(r'^form-testing/$', form_testing),
    url(r'^user-panel/', include(user_panel_urls, namespace="user_panel")),
    url(r'^accounts/', include(accounts_urls, namespace="accounts")),
    url(r'^cfp/', include(cfp_urls, namespace="cfp")),
    url(r'^news/', news_list, name="news"),
    url(r'^accounts/', include('assopy.urls')),
    url(r'^admin/filebrowser/', include(fsite.urls)),
    url(r'^admin/rosetta/', include('rosetta.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^comments/', include('django_comments.urls')),
    url(r'^p3/', include('p3.urls')),
    url(r'^conference/', include('conference.urls')),
    url(r'^conference/talks/(?P<slug>[\w-]+)$', conference_views.talk,
        {'talk_form': pforms.P3TalkForm},
        name='conference-talk'),
    url(r'^conference/speakers/(?P<slug>[\w-]+)', conference_views.speaker,
        {'speaker_form': pforms.P3SpeakerForm},
        name='conference-speaker'),
    url(r'^hcomments/', include('hcomments.urls')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^markitup/', include('markitup.urls')),

    url('', include('social.apps.django_app.urls', namespace='social')),
    # TODO umgelurgel: See if the django.auth.urls are used anywhere and if they can be removed
    url(r'^login/', RedirectView.as_view(pattern_name='auth:login', permanent=False)),
    url('', include('django.contrib.auth.urls', namespace='auth')),

    # production debug panel, doesn't even have a name=
    url(r'^nothing-to-see-here/', include(debugpanel_urls)),
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
