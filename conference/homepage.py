from django.template.response import TemplateResponse


def homepage(request):
    return TemplateResponse(request, 'ep19/homepage.html', {})
