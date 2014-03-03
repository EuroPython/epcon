# -*- coding: UTF-8 -*-
import sys
import os.path
from fabric.api import env, task, get, run, cd
from fabric.contrib import django
sys.path.insert(0, os.path.dirname(env.real_fabfile))

django.project('pycon')
from django.conf import settings

env.use_ssh_config = True
env.hosts = [ 'pycon.it' ]

REMOTE_DEPLOY = '/srv/pycon5/'
REMOTE_PROJECT_DIR = os.path.join(REMOTE_DEPLOY, 'pycon_site/')
REMOTE_DATA_DIR = os.path.join(REMOTE_DEPLOY, 'data/')

@task
def sync_db():
    get(
        os.path.join(REMOTE_DATA_DIR, 'site', 'p3.db'),
        settings.DATABASES['default']['NAME'])

def parent_(path):
    if path[-1] == '/':
        path = path[:-1]
    return os.path.dirname(path)

@task
def sync_media():
    get(
        os.path.join(REMOTE_DATA_DIR, 'media_public'),
        parent_(settings.MEDIA_ROOT))

@task
def deploy():
    with cd(os.path.join(REMOTE_DEPLOY, 'bin')):
        run('update.sh')
