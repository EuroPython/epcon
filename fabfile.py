from fabric.api import env

env.user = 'pyconwww'
env.hosts = ['europython.eu']
env.forward_agent = True

import sys
sys.path.insert(0, '')
from fabric.contrib import django
django.settings_module('pycon.settings')
from django.conf import settings

import os
import os.path
from fabric import api, utils
from fabric.colors import red, green, cyan
from fabric.context_managers import cd, hide, prefix, warn_only
from fabric.contrib import files

class Git(object):
    def resolve_name(self, name='HEAD'):
        """
        Resolves the given name in a commit id
        """
        name = name or 'HEAD'
        with hide('running'):
            return api.local('git rev-parse {}'.format(name), capture=True)

    def check_commit_on_remote(self, commit, remote='origin'):
        """
        Checks if the given commit has been pushed on a remote branch
        """
        remote = remote or 'origin'
        with hide('running'):
            remotes = api.local('git branch -a --contains {}'.format(commit), capture=True)

        needle = 'remotes/{}/'.format(remote)
        for r in remotes.split('\n'):
            if needle in r:
                return True
        return False

    def remote_url(self, remote='origin'):
        remote = remote or 'origin'
        with hide('running'):
            # expected output
            # ---------------
            # origin	git@bitbucket.org:pycod/gepir.git (fetch)
            # origin	git@bitbucket.org:pycod/gepir.git (push)
            remotes = api.local('git remote -v', capture=True)
            for r in remotes.split('\n'):
                try:
                    name, other = r.split('\t', 1)
                except ValueError:
                    continue
                if name == remote:
                    return other.split(' ', 1)[0]

    def clone_repository(self, url):
        with hide('output'):
            api.run("git clone {} .".format(url))

    def update_repository(self):
        with hide('output'):
            api.run("git fetch --all")

    def checkout_commit(self, commit):
        with hide('output'):
            api.run("git checkout {}".format(commit))

    def verify_repository(self):
        with hide('running'), warn_only(), hide('everything'):
            result = api.run('git status')
        return result.return_code == 0

class PyconLayout(object):
    def __init__(self, project_name):
        self.project_name = project_name

    def working_copy(self):
        return '/srv/europython.eu/sites/{}/'.format(self.project_name)

    def virtualenv(self):
        return '/srv/europython.eu/virtualenvs/{}/'.format(self.project_name)

class ProcessManager(object):
    def __init__(self, upstart_name):
        self.name = upstart_name

    def restart(self):
        return api.run('sudo restart {}'.format(self.name))

class DjangoSite(object):
    def __init__(self, project_layout, process_manager, dvcs):
        self.project_layout = project_layout
        self.process_manager = process_manager
        self.dvcs = dvcs

    def run(self, revision=None):
        self.update_code(revision)
        self.update_static_files()
        self.update_database()
        self.restart_site()

    def run_virtualenv(self, cmd, **kw):
        remote_venv = os.path.join(self.project_layout.virtualenv(), 'bin/activate')
        with prefix('source {}'.format(remote_venv)):
            return api.run(cmd, **kw)

    def restart_site(self):
        with hide('output'):
            result = self.process_manager.restart()
            if result.failed:
                print result
                utils.abort(red("{} failed with code {}".format(result.real_command, result.return_code)))

    def update_code(self, revision):
        commit = self.dvcs.resolve_name(revision)
        print green('deploying {}'.format(commit))
        if not self.dvcs.check_commit_on_remote(commit):
            utils.abort(red("commit not found on remote"))

        self.update_remote_working_copy(commit)
        self.update_virtual_env()

    def update_remote_working_copy(self, commit):
        remote_dir = self.project_layout.working_copy()
        print cyan("update remote repository in \"{}\"".format(remote_dir))
        with cd(remote_dir):
            exists = self.dvcs.verify_repository()

        if not exists:
            print cyan("new repository".format(remote_dir), bold=True)
            self._create_remote_repository(remote_dir)
        else:
            self._update_remote_repository(remote_dir)

        with cd(remote_dir):
            self.dvcs.checkout_commit(commit)

    def _update_remote_repository(self, remote_dir):
        with cd(remote_dir):
            self.dvcs.update_repository()

    def _create_remote_repository(self, remote_dir):
        remote_url = self.dvcs.remote_url()
        if remote_url is None:
            utils.abort(red("cannot determine remote url"))

        api.run('mkdir -p {}'.format(remote_dir))
        with cd(remote_dir):
            self.dvcs.clone_repository(remote_url)

    def update_virtual_env(self):
        remote_dir = self.project_layout.working_copy()
        remote_venv = self.project_layout.virtualenv()
        with cd(remote_dir):
            if not files.exists('requirements.txt'):
                print cyan("requirements.txt not found; virtualenv housekeeping skipped")
                return

            print cyan("update remote virtualenv in \"{}\"".format(remote_venv))
            if not files.exists(remote_venv):
                print cyan("new virtualenv", bold=True)
                with hide('output'):
                    api.run("virtualenv --no-site-packages {}".format(remote_venv))

            with hide('output'):
                result = self.run_virtualenv('pip install -r requirements.txt')
                if result.failed:
                    print result
                    utils.abort(red("{} failed with code {}".format(result.real_command, result.return_code)))

    def update_static_files(self):
        self.collect_static()

    def collect_static(self):
        remote_dir = self.project_layout.working_copy()
        with cd(remote_dir):
            with hide('output'):
                result = self.run_virtualenv('./manage.py collectstatic --noinput --link')
                if result.failed:
                    print result
                    utils.abort(red("{} failed with code {}".format(result.real_command, result.return_code)))

    def update_database(self):
        remote_dir = self.project_layout.working_copy()
        with cd(remote_dir):
            with hide('output'):
                result = self.run_virtualenv('./manage.py migrate')
                if result.failed:
                    print result
                    utils.abort(red("{} failed with code {}".format(result.real_command, result.return_code)))

@api.task
def deploy_beta(revision='develop'):
    site = PyconLayout('beta')
    remote = DjangoSite(site, ProcessManager('beta-pyconit'), Git())
    remote.run(revision=revision)

@api.task
def deploy(revision='HEAD'):
    site = PyconLayout('production')
    remote = DjangoSite(site, ProcessManager('pyconit'), Git())
    remote.run(revision=revision)

@api.task
def sync_db():
    site = PyconLayout('production')
    remote_db = os.path.join(site.working_copy(), 'data', 'site', 'p3.db')
    api.get(
        remote_db,
        settings.DATABASES['default']['NAME'])
