# -*- coding: UTF-8 -*-
from django import forms
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt

# see: http://www.djangosnippets.org/snippets/821/
def render_to(template):
    """
    Decorator for Django views that sends returned dict to render_to_response function
    with given template and RequestContext as context instance.

    If view doesn't return dict then decorator simply returns output.
    Additionally view can return two-tuple, which must contain dict as first
    element and string with template name as second. This string will
    override template name, given as parameter

    Parameters:

     - template: template name to use
    """
    def renderer(func):
        def wrapper(request, *args, **kw):
            output = func(request, *args, **kw)
            if isinstance(output, (list, tuple)):
                return render_to_response(output[1], output[0], RequestContext(request))
            elif isinstance(output, dict):
                return render_to_response(template, output, RequestContext(request))
            return output
        return wrapper
    return renderer

class LoginForm(auth.forms.AuthenticationForm):
    email = forms.EmailField()

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        del self.fields['username']

    def clean(self):
        data = self.cleaned_data
        if data.get('email') and data.get('password'):
            user = auth.authenticate(email=data['email'], password=data['password'])
            self.user_cache = user
            if user is None:
                raise forms.ValidationError('Invalid credentials')
            elif not user.is_active:
                raise forms.ValidationError('This account is inactive.')
        return data

class PasswordLostForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        data = self.cleaned_data
        try:
            self.user = auth.models.User.objects.get(email=data['email'])
        except:
            raise forms.ValidationError('email non valida')
        return data['email']

@login_required
@render_to('assopy/home.html')
def home(request):
    return {}

@csrf_exempt
def janrain_token(request):
    pass
