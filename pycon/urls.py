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

from conference.accounts import urlpatterns as accounts_urls
from conference.cart import urlpatterns_ep19 as cart19_urls
from conference.cfp import urlpatterns as cfp_urls
from conference.debug_panel import urlpatterns as debugpanel_urls
from conference.homepage import (
    generic_content_page,
    generic_content_page_with_sidebar,
    homepage,
)
from conference.news import news_list
from conference.talk_voting import urlpatterns as talk_voting_urls
from conference.user_panel import urlpatterns as user_panel_urls
from conference.talks import urlpatterns as talks_urls
from conference.profiles import urlpatterns as profiles_urls
from conference.schedule import urlpatterns as schedule_urls
from conference.social_card import urlpatterns as social_urls

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
    url(r'^admin/', include(admin.site.urls)),
    url(r'^cart/', include(cart19_urls, namespace="cart")),
    url(r'^p3/', include('p3.urls')),
    url(r'^conference/', include(social_urls)),
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
