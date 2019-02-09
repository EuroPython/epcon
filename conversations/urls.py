
from django.conf.urls import url, include
from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse


@staff_member_required
def conversations_staff_homepage(request):
    return TemplateResponse(
        request, "ep19/conversations/home.html", {}
    )


urlpatterns = [
    url(
        r"^user/",
        include(
            "conversations.user_interface", namespace="user_conversations"
        ),
    ),
    url(
        r"^staff/$",
        conversations_staff_homepage,
        name="conversations_staff_homepage"
    ),
    url(
        r"^staff/helpdesk/",
        include(
            "conversations.helpdesk.staff_panel", namespace="staff_helpdesk"
        ),
    )
]
