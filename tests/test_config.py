# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Tests for loading, validating, and saving the configuration
"""

from copy import deepcopy
from collections import OrderedDict
import os

import pytest

from ipadocker import config, constants


# TODO: this could be more sane
CONFIG_DATA = {
    'valid_config': {
        'data': deepcopy(constants.DEFAULT_CONFIG),
    },
    'extra_section': {
        'data': deepcopy(constants.DEFAULT_CONFIG),
        'raises': {
            'type': config.UnknownOption,
            'path': ()
        },
    },
    'extra_subsection': {
        'data': deepcopy(constants.DEFAULT_CONFIG),
        'raises': {
            'type': config.UnknownOption,
            'path': ('host',)
        }
    },
    'invalid_value': {
        'data': deepcopy(constants.DEFAULT_CONFIG),
        'raises': {
            'type': config.InvalidValueType,
            'path': ()
        }
    },
    'invalid_nested_value': {
        'data': deepcopy(constants.DEFAULT_CONFIG),
        'raises': {
            'type': config.InvalidValueType,
            'path': ('container',)
        }
    }
}

CONFIG_DATA['extra_section']['data'].update({'extra_section': 'extra_value'})
CONFIG_DATA['extra_subsection']['data']['host'].update(
    {'extra_subsection': 'extra_value'})
CONFIG_DATA['invalid_value']['data']['git_repo'] = 42
CONFIG_DATA['invalid_nested_value']['data']['container']['detach'] = 42


@pytest.fixture(params=[data for data in CONFIG_DATA.values()])
def config_dict(request):
    """
    Yield individual config data from CONFIG_DATA
    """
    return request.param


def test_config_validation(config_dict):
    """
    test that the config validation works as intended
    """
    if 'raises' in config_dict:
        with pytest.raises(config_dict['raises']['type']) as e:
            config.validate_config(config_dict['data'],
                                   constants.DEFAULT_CONFIG)

        assert e.value.path == config_dict['raises']['path']

    else:
        config.validate_config(config_dict['data'], constants.DEFAULT_CONFIG)


def test_config_overrides():
    overrides = {
        'git_repo': 'custom/repo',
        'container': {
            'image': 'custom-image'
        },
        'host': {
            'tmpfs': ['/var/tmp']
        },
        'server': {
            'domain': 'example.org'
        }
    }

    test_config = config.IPADockerConfig(overrides)

    for key, value in overrides.items():
        if isinstance(value, dict):
            for key2, value2 in overrides[key].items():
                assert test_config[key][key2] == value2
        else:
            assert test_config[key] == value


IPA_RUN_TESTS_CONFIGS = {
    ('--verbose', '--ignore', 'test_integration'): OrderedDict(
        (
            ('verbose', True),
            ('ignore', ['test_integration'])
        )
    ),
    ('--ignore', 'test_integration', '--ignore', 'test_webui'): OrderedDict(
        (
            ('verbose', False),
            ('ignore', ['test_integration', 'test_webui'])
        )
    ),
}


@pytest.fixture(params=IPA_RUN_TESTS_CONFIGS.items())
def ipa_run_tests_config(request):
    """
    yield data mocking 'tests' section in config along with the expected list
    of CLI params
    """
    return request.param[0], {'tests': request.param[1]}


def test_run_test_config_parsing(ipa_run_tests_config):
    expected, test_config = ipa_run_tests_config
    run_tests_args = config.get_ipa_run_tests_options(test_config)

    assert run_tests_args == list(expected)


@pytest.fixture()
def ipaconfig(request):
    """
    Default config
    """
    return config.IPADockerConfig()


def test_write_config(ipaconfig):
    """
    test that we can write the default config to file
    """
    config_file = 'test.yaml'
    with open('test.yaml', 'w') as f:
        ipaconfig.write_config(f)

    try:
        os.unlink(config_file)
    except OSError:
        pass
