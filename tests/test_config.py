# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Tests for loading, validating, and saving the configuration
"""

from copy import deepcopy
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
