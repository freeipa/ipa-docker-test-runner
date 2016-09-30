# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

from collections import ChainMap
import logging
import os

import yaml

from ipadocker import constants

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """
    Base class for config validation errors

    :param msg: error message
    :param path: path traversed during configuration validation
    """
    def __init__(self, msg, path):
        self.path = path
        super(ConfigValidationError, self).__init__(msg)


class UnknownOption(ConfigValidationError):
    """
    Raised when unknown option is encountered in config

    :param option: option name
    :param path: see `ConfigValidationError`
    """
    def __init__(self, option, path):
        msg = "Unrecognized option name: {} (path {})".format(
            option, path)
        super(UnknownOption, self).__init__(msg, path)


class InvalidValueType(ConfigValidationError):
    """
    Raised when the value of option does not match the expected type

    :param option: option name
    :param expected: expected type
    :param got: type got from config
    :param path: see `ConfigValidationError`
    """
    def __init__(self, option, expected, got, path):
        msg = ("Invalid type for option: {}: expected {}, got {} "
               "(path {})".format(option, expected, got, path))
        super(InvalidValueType, self).__init__(msg, path)


def validate_config(config, defaults, path=()):
    """
    Validate a config dictionary against a schema currently comprised from set
    of defaults in `ipadocker.constants` module. More sophisticated schema
    matching may be implemented in the future

    :param config: configuration dictionary
    :param defaults: default config serving as reference
    :param path: Initially an empty tuple. When nested dictionaries are
    traversed `path` holds a stack of already visited levels
    :param logger: Logger to use (default `None`, i. e. use module-level
    logger)

    :raises: UnknownOption when an unknown option is encountered and
    InvalidValueType when the option value has unexpected type
    """

    for option, value in config.items():
        logger.debug("Validating option %s: value: %s", option, value)
        if option not in defaults:
            raise UnknownOption(option, path)

        if not isinstance(value, type(defaults[option])):
            raise InvalidValueType(
                option, type(value), type(defaults[option]), path)

        if isinstance(value, dict):
            sub_path = path + (option,)
            sub_config = config[option]
            sub_defaults = defaults[option]

            logger.debug("Traversing into path: %s", sub_path)
            validate_config(sub_config, sub_defaults, sub_path)


def load_config_from_file(input_file):
    """
    Validate and load configuration from opened YaML file

    :param input_file: file-like object open for reading
    :param logger: logger to use (defaults to None, i.e. use module-level
    logger)

    :returns: dictionary of parsed values
    """
    logger.info("Parsing YAML configuration")
    config = yaml.safe_load(input_file)
    logger.debug("Retrieved configuration: %s", config)
    logger.info("Validating retrieved configuration")

    validate_config(config, constants.DEFAULT_CONFIG)

    return config


def load_default_config_file():
    """
    Validate and load default config file specified by
    `ipadocker.constants.DEFAULT_CONFIG_FILE` constant

    :param logger: logger to use (defaults to None, i.e. use module-level
    logger)

    :returns: empty dict if the file does not exist or a dict of parsed options
    """
    default_config_file = constants.DEFAULT_CONFIG_FILE
    if not os.path.isfile(default_config_file):
        logger.info("File %s does not exist, skipping", default_config_file)
        return {}

    with open(default_config_file, 'r') as input_file:
        logger.info("Parsing configuration file %s", default_config_file)
        return load_config_from_file(input_file)


class IPADockerConfig(object):
    """
    An object which encapsulates the merged default options and options
    gathered from other sources (currently only default config, more may come
    in the future). The config is implemented as a ChainMap so that more
    specific overrides are searched first and default values are returned last

    The config items can be retrieved using dict access with keys
    """
    def __init__(self):
        self.config = ChainMap(load_default_config_file(),
                               constants.DEFAULT_CONFIG)

        logger.debug("Flat configuration: %s", self.to_dict())

    def __getitem__(self, item):
        try:
            return self.config[item]
        except KeyError:
            raise AttributeError

    def to_dict(self):
        """
        Squash the config to single dict and return that
        """
        return {k: v for k, v in self.config.items()}

    def write_config(self, output_file):
        """
        Dump the current configuration to file as YaML

        :param f: file-like object open for writing
        """
        logger.info("Dumping YAML configuration")
        yaml.safe_dump(self.to_dict(), output_file, default_flow_style=False)
