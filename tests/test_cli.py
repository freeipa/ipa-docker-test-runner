# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Tests for CLI frontend
"""

import os
import tempfile

import pytest
import yaml

from ipadocker import cli, constants


def root_function(stack, args):
    """
    root function and the first prerequisite
    """
    stack.append('root')


@cli.prerequisite(root_function)
def next_function(stack, args):
    """
    Function whose call should execute root_function first
    """
    stack.append('next')


@cli.prerequisite(next_function)
def final_function(stack, args):
    """
    Function whose call should execute root_function and next_function first
    """
    stack.append('final')


def next_function2(stack, args):
    """
    Alternative implementation for multiple-prerequisites test
    """
    stack.append('next2')


@cli.prerequisite(root_function, next_function2)
def final_function2(stack, args):
    """
    function with two prerequisites, i.e. root_function and next_function2
    should be executed prior to call itself
    """
    stack.append('final2')


@cli.prerequisite(root_function, next_function)
def final_function3(stack, args):
    """
    This one should call root_function twice, then next_function
    """
    stack.append('final3')


@pytest.fixture(scope='function')
def call_stack(request):
    """
    Simulation of the function call stack. Each of them should push some string
    on it when called
    """
    return []


@pytest.fixture()
def arguments():
    """
    dummy arguments
    """
    return 'args'


def test_root_function(call_stack, arguments):
    """
    test that root function will leave only one item in the stack
    """
    root_function(call_stack, arguments)
    assert call_stack == ['root']


def test_next_function(call_stack, arguments):
    """
    next_function() should leave 'root' and 'next' in the stack
    """
    next_function(call_stack, arguments)
    assert call_stack == ['root', 'next']


def test_final_function(call_stack, arguments):
    """
    final_function() should leave thee items in the stack
    """
    final_function(call_stack, arguments)
    assert call_stack == ['root', 'next', 'final']


def test_final2_function(call_stack, arguments):
    """
    final_function() should also leave thee items in the stack
    """
    final_function2(call_stack, arguments)
    assert call_stack == ['root', 'next2', 'final2']


def test_final3_function(call_stack, arguments):
    """
    final_function() should call root_function twice
    """
    final_function3(call_stack, arguments)
    assert call_stack == ['root', 'root', 'next', 'final3']


CLI_ARGUMENTS = {
    'build --developer-mode --make-target=lint': {
        'args': {
            'developer_mode': True,
            'make_target': 'lint'
        },
        'action': cli.build
    },
    'sample-config': {
        'action': cli.sample_config
    },
    ('run-tests test_xmlrpc/test_caacl_plugin.py '
     'test_integration/test_forced_client_reenrollment.py'): {
         'args': {
             'path': [
                 'test_xmlrpc/test_caacl_plugin.py',
                 'test_integration/test_forced_client_reenrollment.py'
             ]
         },
         'action': cli.run_tests
     },
    '--debug run-tests': {
        'action': cli.run_tests,
        'args': {
            'path': [],
            'debug': True
        }
    },
    '--container-image custom-image --git-repo git/repo run-tests': {
        'action': cli.run_tests,
        'args': {
            'path': [],
            'cli_overrides': {
                'git_repo': 'git/repo',
                'container': {
                    'image': 'custom-image'
                }
            }
        }
    }
}


@pytest.fixture(params=[(a, res) for a, res in CLI_ARGUMENTS.items()])
def cli_args(request):
    """
    Yield CLI arguments from CLI_ARGUMENTS
    """
    return request.param


@pytest.fixture()
def parser():
    """
    Create CLI frontend parser
    """
    return cli.make_parser()


TEST_IMAGE_LATEST = 'test-image:latest'
TEST_INSTALL_STEP = ['dnf install -y freeipa-server --best --allowerasing']
TEST_GIT_REPO = '/test/repo.git'

TEST_CONFIG_VALUES = {
    'git_repo': TEST_GIT_REPO,
    'container': {
        'image': TEST_IMAGE_LATEST
    },
    'host': {
        'privileged': False
    },
    'steps': {
        'install_packages': TEST_INSTALL_STEP
    }
}


@pytest.yield_fixture()
def config_file():
    """
    Generate a sample config file with overrides
    """
    fd, config_filename = tempfile.mkstemp()
    os.close(fd)

    try:
        with open(config_filename, 'w') as test_config:
            yaml.safe_dump(TEST_CONFIG_VALUES, test_config,
                           default_flow_style=False)
        yield config_filename
    finally:
        try:
            os.remove(config_filename)
        except OSError:
            pass


def test_config_file_cli_arg_override(parser, config_file):
    """
    Test overriding from config file and CLI args
    """
    args_w_config_override = parser.parse_args(['-c', config_file, 'build'])

    config_obj = cli.create_ipaconfig(args_w_config_override)

    assert config_obj['container']['image'] == TEST_IMAGE_LATEST
    assert config_obj['git_repo'] == TEST_GIT_REPO
    assert config_obj['steps']['install_packages'] == TEST_INSTALL_STEP

    overriden_image = 'overriden-image:cli'
    args_w_cli_override = parser.parse_args(['-c', config_file,
                                             '--container-image',
                                             overriden_image,
                                             'install-server'])
    config_obj = cli.create_ipaconfig(args_w_cli_override)
    assert config_obj['container']['image'] == overriden_image
    assert (
        config_obj['steps']['install_packages'] ==
        TEST_CONFIG_VALUES['steps']['install_packages'])
    assert (
        config_obj['container']['working_dir'] == constants.FREEIPA_MNT_POINT)


def test_cli_args(parser, cli_args):
    """
    Test that all CLI arguments are parsed properly
    """
    parsed_args = parser.parse_args(cli_args[0].split())

    action = cli.get_action(parsed_args.action_name)
    assert action is cli_args[1]['action']

    if 'args' not in cli_args[1]:
        return

    for item, value in cli_args[1]['args'].items():
        assert getattr(parsed_args, item) == value
