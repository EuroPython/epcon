
from django.conf.urls import url, include


urlpatterns = [
    url(
        r"^staff/helpdesk/",
        include(
            "conversations.helpdesk.staff_panel", namespace="staff_helpdesk"
        ),
    )
]
