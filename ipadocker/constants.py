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

DEFAULT_CONFIG_FILE = os.path.expanduser('~/.ipa_docker_config.yaml')

DEFAULT_IMAGE = 'martbab/freeipa-fedora-test-runner:master_latest'

DEFAULT_GIT_REPO = '/path/to/repo'

DEFAULT_CONTAINER_CONFIG = {
    'image': DEFAULT_IMAGE,
    'hostname': 'master.ipa.test',
    'detach': True,
    'working_dir': FREEIPA_MNT_POINT
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

DEFAULT_CONFIG = {
    'git_repo': DEFAULT_GIT_REPO,
    'container': DEFAULT_CONTAINER_CONFIG,
    'host': DEFAULT_HOST_CONFIG,
    'server': DEFAULT_SERVER_CONFIG,
    'tests': DEFAULT_IPA_RUN_TEST_CONFIG
}
