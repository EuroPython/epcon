
from django.conf.urls import url, include


urlpatterns = [
    url(
        r"^helpdesk/", include("conversations.helpdesk", namespace="helpdesk")
    )
]
