# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Tests for CLI frontend
"""

import pytest

from ipadocker import cli


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
