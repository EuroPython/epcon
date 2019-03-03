from django.conf.urls import url
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required


@login_required
def user_dashboard(request):

    return TemplateResponse(
        request, "ep19/bs/user_panel/dashboard.html", {}
    )


urlpatterns = [
    url(r'^$', user_dashboard, name="dashboard"),
]
