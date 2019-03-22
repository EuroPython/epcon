from django.template.response import TemplateResponse
from django.utils.lorem_ipsum import words, paragraphs
from django import forms


def homepage(request):
    return TemplateResponse(
        request, 'ep19/bs/homepage/home.html', {}
    )


def generic_content_page(request):
    return TemplateResponse(
        request, 'ep19/bs/content/generic_content_page.html', {
            'lorem_words': words,
            'lorem_paragraphs': paragraphs,
        }
    )


def generic_content_page_with_sidebar(request):
    return TemplateResponse(
        request, 'ep19/bs/content/generic_content_page_with_sidebar.html', {
            'lorem_words': words,
            'lorem_paragraphs': paragraphs,
        }
    )


def form_testing(request):

    class AForm(forms.Form):
        name = forms.CharField()
        password = forms.CharField(widget=forms.widgets.PasswordInput)
        email = forms.EmailField()
        textarea = forms.CharField(widget=forms.widgets.Textarea)

    return TemplateResponse(
        request, 'ep19/bs/form_testing.html', {
            'form': AForm()
        }
    )
