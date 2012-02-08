# -*- coding: UTF-8 -*-

import os.path
import string
import random

from fabric.api import *
from fabric.contrib import files

env.hosts = [ 'pycon.it' ]

# sshagent_run credits to http://lincolnloop.com/blog/2009/sep/22/easy-fabric-deployment-part-1-gitmercurial-and-ssh/
# modified by dvd :)
def sshagent_run(cmd, capture=True):
    """
    Helper function.
    Runs a command with SSH agent forwarding enabled.
    
    Note:: Fabric (and paramiko) can't forward your SSH agent. 
    This helper uses your system's ssh to do so.
    """

    cwd = env.get('cwd', '')
    if cwd:
        cmd = 'cd %s;%s' % (cwd, cmd)

    with settings(cwd=''):
        for h in env.hosts:
            try:
                # catch the port number to pass to ssh
                host, port = h.split(':')
                local('ssh -p %s -A %s "%s"' % (port, host, cmd), capture=capture)
            except ValueError:
                local('ssh -A %s "%s"' % (h, cmd), capture=capture)

def download_db():
    get('/srv/europython/db/p3.db', './')

