from django.conf.urls import url

from p3 import views as p3_views


urlpatterns = [
    url(r'^p/profile/(?P<slug>[\w-]+)/avatar$', p3_views.p3_profile_avatar, name='p3-profile-avatar'),
]
