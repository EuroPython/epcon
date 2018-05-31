# coding: utf-8

"""
Things in this file are related to a special debug panel that helps us debug
things in production.
"""

import platform
import subprocess

import django
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.template.response import TemplateResponse


def get_current_commit_hash():
    command = 'git rev-parse HEAD'
    process = subprocess.Popen(
        command.split(), stdout=subprocess.PIPE, cwd=settings.PROJECT_DIR
    )
    return process.communicate()[0]


@staff_member_required
def debug_panel(request):

    debug_vars = [
        ('Current_Commit_Hash', get_current_commit_hash()),
        ('Django_Version', django.VERSION),
        ('Python_Version', platform.python_version()),
    ]

    allowed_settings = [
        'ADMINS',
        'DATA_DIR',
        'PROJECT_DIR',
        'DEFAULT_FROM_EMAIL',
        'SERVER_EMAIL',
    ]

    for setting_name in allowed_settings:
        debug_vars.append(
            (setting_name, getattr(settings, setting_name))
        )

    return TemplateResponse(request, "conference/debugpanel.html", {
        'debug_vars': debug_vars
    })
