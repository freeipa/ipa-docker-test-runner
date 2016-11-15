# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Tests for command execution logic
"""

import pytest

from ipadocker import cli, command, config, constants


@pytest.fixture
def ipaconfig():
    """
    flattened default IPA config
    """
    return config.IPADockerConfig()


@pytest.fixture()
def flattened_config(request, ipaconfig):
    return ipaconfig.flatten()


DEFAULT_BUILDS_SUBSTITUTED = {
    'build': ['make {c.DEFAULT_MAKE_TARGET}'.format(c=cli)],
    'install_server': [
        ('ipa-server-install -U --domain ipa.test '
         '--realm IPA.TEST -p Secret123 -a Secret123 '
         '--setup-dns --auto-forwarders'),
        'ipa-kra-install -p Secret123'
    ],
}


@pytest.fixture(
    params=[(k, v) for k, v in DEFAULT_BUILDS_SUBSTITUTED.items()])
def substituted_commands(request):
    return request.param


@pytest.fixture
def default_namespace(request, substituted_commands):
    parser = cli.make_parser()
    subcommand_name = substituted_commands[0].replace('_', '-')
    args = parser.parse_args([subcommand_name])
    return vars(args)


def test_execution_step_instantiation(ipaconfig, flattened_config,
                                      substituted_commands, default_namespace):
    step_name, commands = substituted_commands
    command_templates = ipaconfig['steps'][step_name]

    step = command.ExecutionStep(command_templates, flattened_config,
                                 **default_namespace)

    assert step.commands == commands


def test_invalid_template_string(flattened_config):
    with pytest.raises(KeyError):
        command.ExecutionStep(['make ${invalid_var}'], flattened_config)
