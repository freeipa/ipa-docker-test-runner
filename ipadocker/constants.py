# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Default constants
"""

import os


FREEIPA_MNT_POINT = os.path.join('/', 'freeipa')
SYS_FS_CGROUP = os.path.join('/', 'sys', 'fs', 'cgroup')
DEV_URANDOM = os.path.join('/', 'dev', 'urandom')
DEV_RANDOM = os.path.join('/', 'dev', 'random')
TMP = os.path.join('/', 'tmp')
RUN = os.path.join('/', 'run')

APP_NAME = 'ipa-docker-test-runner'

CONFIG_ROOT = os.environ.get(
    'XDG_CONFIG_HOME', os.path.expanduser('~/.config'))

CONFIG_DIR = os.path.join(CONFIG_ROOT, APP_NAME)

DEFAULT_CONFIG_FILE = os.path.join(
    CONFIG_DIR,
    'config.yaml'
)

DEFAULT_IMAGE = 'martbab/freeipa-fedora-test-runner:master-latest'

DEFAULT_GIT_REPO = '/path/to/repo'

DEFAULT_CONTAINER_CONFIG = {
    'image': DEFAULT_IMAGE,
    'hostname': 'master.ipa.test',
    'detach': True,
    'working_dir': FREEIPA_MNT_POINT,
    'environment': []
}

DEFAULT_HOST_CONFIG = {
    'binds': [
        ':'.join([SYS_FS_CGROUP, SYS_FS_CGROUP, 'ro']),
        ':'.join([DEV_URANDOM, DEV_RANDOM, 'ro'])
    ],
    'tmpfs': [TMP, RUN],
    'privileged': False,
    'security_opt': ['label:disable']
}

DEFAULT_SERVER_CONFIG = {
    'domain': 'ipa.test',
    'realm': 'IPA.TEST',
    'setup_dns': True,
    'password': 'Secret123'
}

DEFAULT_IPA_RUN_TEST_CONFIG = {
    'ignore': [
        'test_integration',
        'test_webui',
        'test_ipapython/test_keyring.py',
    ],
    'verbose': True
}

DEFAULT_STEP_CONFIG = {
    'builddep': [
        'dnf builddep -y ${builddep_opts} --spec freeipa.spec.in',
    ],
    'tox': [
        'tox'
    ],
    'configure': [
        'autoreconf -i && ./configure',
    ],
    'lint': [
        'make lint'
    ],
    'webui_unit': [
        'dnf install -y npm'
        'cd ${container_working_dir}/install/ui/js/libs && make',
        'cd ${container_working_dir}/install/ui && npm install',
        ('cd ${container_working_dir}/install/ui && '
         'node_modules/grunt/bin/grunt --verbose qunit')
    ],
    'build': [
        'make ${make_target}'
    ],
    'install_packages': [
        ('dnf install -y ${container_working_dir}/dist/rpms/*.rpm --best '
         '--allowerasing')
    ],
    'install_server': [
        ('ipa-server-install -U --domain ${server_domain} '
         '--realm ${server_realm} -p ${server_password} -a ${server_password} '
         '--setup-dns --auto-forwarders'),
        'ipa-kra-install -p ${server_password}',
        ('ipa-adtrust-install -U --enable-compat --add-sids '
         '-a ${server_password}')
    ],
    'prepare_tests': [
        'echo ${server_password} | kinit admin && ipa ping',
        'cp -r /etc/ipa/* /root/.ipa/.',
        'echo ${server_password} > /root/.ipa/.dmpw'
    ],
    'run_tests': [
        'ipa-run-tests ${tests_ignore} ${tests_verbose} ${path}'
    ],
    'cleanup': [
        'chown -R ${uid}:${gid} ${container_working_dir}'
    ]
}

DEFAULT_CONFIG = {
    'git_repo': DEFAULT_GIT_REPO,
    'container': DEFAULT_CONTAINER_CONFIG,
    'host': DEFAULT_HOST_CONFIG,
    'server': DEFAULT_SERVER_CONFIG,
    'tests': DEFAULT_IPA_RUN_TEST_CONFIG,
    'steps': DEFAULT_STEP_CONFIG
}
