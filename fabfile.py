from fabric.api import env

env.user = 'eyad'
env.hosts = ['136.243.32.71']
env.forward_agent = True

import sys
sys.path.insert(0, '')

from fabric import api, utils
from fabric.operations import sudo
from fabric.colors import red


class Container(object):
    def __init__(self, container_name):
        self.container_name = container_name
        self.base_run = 'docker exec {} '.format(self.container_name)

    def run(self, command):
        command_to_run = self.base_run + command
        return sudo(command_to_run)


class DjangoSite(object):
    def __init__(self, container):
        self.container = container

    def run(self):
        self.update_code()
        self.collect_static()
        self.update_database()
        self.restart_site()

    def restart_site(self):
        sudo('docker stop {}'.format(self.container.container_name))
        sudo('docker start {}'.format(self.container.container_name))

    def update_code(self):
        result = self.container.run('git pull')
        if result.failed:
            print result
            utils.abort(red("{} failed with code {}".format(result.real_command, result.return_code)))

    def update_virtual_env(self):
        result = self.container.run('pip install -r requirements.txt')
        if result.failed:
            print result
            utils.abort(red("{} failed with code {}".format(result.real_command, result.return_code)))

    def update_static_files(self):
        self.collect_static()

    def collect_static(self):
        result = self.container.run('./manage.py collectstatic --noinput --link')
        if result.failed:
            print result
            utils.abort(red("{} failed with code {}".format(result.real_command, result.return_code)))

    def update_database(self):
        result = self.container.run('./manage.py migrate')
        if result.failed:
            print result
            utils.abort(red("{} failed with code {}".format(result.real_command, result.return_code)))


@api.task
def deploy_beta():
    site = Container('python_python_1')
    remote = DjangoSite(site)
    remote.run()


@api.task
def deploy():
    site = Container('python_python_1')
    remote = DjangoSite(site)
    remote.run()

# @api.task
# def sync_db():
#     site = PyconLayout('production')
#     remote_db = os.path.join(site.working_copy(), 'data', 'site', 'p3.db')
#     api.get(
#         remote_db,
#         settings.DATABASES['default']['NAME'])
