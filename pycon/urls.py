from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.views import defaults, static
from django.views.generic import RedirectView
from django.urls import re_path

from filebrowser.sites import site as fsite

from conference.accounts import urlpatterns as accounts_urls
from conference.cart import urlpatterns_ep19 as cart_urls
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
    re_path(r'^$', homepage, name='homepage'),
    re_path(r'^generic-content-page/$', generic_content_page),
    re_path(r'^generic-content-page/with-sidebar/$', generic_content_page_with_sidebar),
    re_path(r'^user-panel/', include((user_panel_urls, 'user_panel'), namespace="user_panel")),
    re_path(r'^accounts/', include((accounts_urls, 'accounts'), namespace="accounts")),
    re_path(r'^cfp/', include((cfp_urls, 'cfp'), namespace="cfp")),
    re_path(r'^talks/', include((talks_urls, 'talks'), namespace="talks")),
    re_path(r'^profiles/', include((profiles_urls, 'profiles'), namespace="profiles")),
    re_path(r'^talk-voting/', include((talk_voting_urls, 'talk_voting'), namespace="talk_voting")),
    re_path(r'^schedule/', include((schedule_urls, 'schedule'), namespace="schedule")),
    re_path(r'^news/', news_list, name="news"),
    re_path(r'^accounts/', include('assopy.urls')),
    re_path(r'^admin/filebrowser/', fsite.urls),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^cart/', include((cart_urls, 'cart'), namespace="cart")),
    re_path(r'^p3/', include('p3.urls')),
    re_path(r'^conference/', include((social_urls, 'social_urls'))),
    re_path(r'^i18n/', include('django.conf.urls.i18n')),

    re_path('', include('social.apps.django_app.urls', namespace='social')),
    # TODO umgelurgel: See if the django.auth.urls are used anywhere and if they can be removed
    re_path(r'^login/', RedirectView.as_view(pattern_name='auth:login', permanent=False)),
    re_path('', include(('django.contrib.auth.urls', 'auth'), namespace='auth')),

    # production debug panel, doesn't even have a name=
    re_path(r'^nothing-to-see-here/', include((debugpanel_urls, 'debugpanel'))),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^media/(?P<path>.*)$",
            static.serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
        re_path(
            r"^500/$", defaults.server_error, kwargs={"exception": Exception()}
        ),
        re_path(
            r"^404/$",
            defaults.page_not_found,
            kwargs={"exception": Exception()},
        ),
        re_path(
            r"^403/$",
            defaults.permission_denied,
            kwargs={"exception": Exception()},
        ),
        re_path(
            r"^400/$", defaults.bad_request, kwargs={"exception": Exception()}
        ),
    ]

urlpatterns += [
    re_path(r'^', include('cms.urls')),
]
