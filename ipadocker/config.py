# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

from collections import ChainMap
import itertools
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


def get_ipa_run_tests_options(config):
    """
    Get a list of ipa-run-tests options from the IPADockerConfig object

    :param config: IPADockerConfig instance

    :returns: list of options parsed from the 'tests' section of the config
    """

    result = []
    for key, value in config['tests'].items():
        opt_name = '--{}'.format(key.replace('_', '-'))

        if isinstance(value, (list, tuple)):
            for i in itertools.product([opt_name], value):
                result.extend(i)

        elif isinstance(value, bool) and value:
            result.append(opt_name)

        elif isinstance(value, bool) and not value:
            continue
        else:
            result.extend([opt_name, value])

    return result


class DeepChainMap(ChainMap):
    """
    ChainMap implementation that supports overriding of nested dictionaries

    Adapted from
    http://www.saltycrane.com/blog/2014/02/recursive-chained-map-lookups/
    """
    def __getitem__(self, key):
        values = []
        for mapping in self.maps:
            try:
                values.append(mapping[key])
            except KeyError:
                pass
        if not values:
            raise KeyError

        first = values.pop(0)
        result = first

        if isinstance(first, dict):
            values = [x for x in values if isinstance(x, dict)]
            if values:
                values.insert(0, first)
                result = self.__class__(*values)

        return result

    def to_dict(self):
        result = {}
        for key, value in self.items():
            if isinstance(value, self.__class__):
                result[key] = value.to_dict()
            else:
                result[key] = value

        return result


def flatten_mapping(mapping, separator='_', path=()):
    """
    Flatten a nested mapping, i.e. return a flat dict by transforming keys

    :param mapping: nested mapping to transform
    :param separator: separator which will be used in key concatenation from
        nested mapping
    :param path: stack holding keys of previous nesting levels

    :returns: one-level mappings with the keys constructed from nested
        dictionary keys by concatenation with separator
    """
    flat_mapping = {}

    for key, value in mapping.items():
        if isinstance(value, dict):
            new_path = path + (key,)
            flat_mapping.update(
                flatten_mapping(
                    mapping[key], separator=separator, path=new_path))
        else:
            items = path + (key,)
            flat_key = separator.join(items)
            flat_mapping[flat_key] = value

    return flat_mapping


def deepen_mapping(mapping, separator='_',
                   reference=None, path=()):
    """
    re-create a nested mapping from a flat representation created by
    @flatten_mapping. A reference dictionary is needed to unambiguously
    construct all paths

    :param mapping: flat mapping to transform
    :param separator: separator that was used to concatenate keys in the
        original nested mapping
    :param path: stack holding keys of previous nesting levels
    """
    if reference is None:
        reference = constants.DEFAULT_CONFIG

    deep_mapping = {}

    key_prefix = ''

    if path:
        key_prefix = separator.join(path)

    for key, value in reference.items():
        path_to_set = path + (key,)
        if isinstance(value, dict):
            deep_mapping[key] = deepen_mapping(
                mapping,
                separator=separator,
                reference=value,
                path=path_to_set)
        else:
            flat_key = separator.join([key_prefix, key]) if key_prefix else key
            if flat_key in mapping:
                deep_mapping[key] = mapping[flat_key]

    return deep_mapping


class IPADockerConfig(object):
    """
    An object which encapsulates the merged default options and options
    gathered from other sources (currently only default config, more may come
    in the future). The config is implemented as a ChainMap so that more
    specific overrides are searched first and default values are returned last

    The config items can be retrieved using dict access with keys
    """
    def __init__(self, *overrides):
        """
        the contents of default config file and default values from
        constants.py are appended to the overrides as fallbacks
        """
        overrides += (load_default_config_file(), constants.DEFAULT_CONFIG)
        self.config = DeepChainMap(*overrides)

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
        return self.config.to_dict()

    def flatten(self, separator='_'):
        """
        return a flat dict representing the config. The keys in this one level
        representation are in the form separated by underscores
        (e.g. config['container']['image'] becomes
        flat_config['container{separator}image']

        :param separator: a string that will be use to concatenate nested keys
        :returns flattened view of the config:
        """
        return flatten_mapping(self.config.to_dict(), separator=separator)

    def write_config(self, output_file):
        """
        Dump the current configuration to file as YaML

        :param f: file-like object open for writing
        """
        logger.info("Dumping YAML configuration")
        yaml.safe_dump(self.to_dict(), output_file, default_flow_style=False)


def opt_name_to_override(name, overriden_value, override_dict,
                         reference=constants.DEFAULT_CONFIG, path=()):
    transformed_name = name
    if not path:
        transformed_name = name.replace('-', '_')[2:]

    for key, value in reference.items():
        if transformed_name.startswith(key):
            if isinstance(value, dict):
                if key not in override_dict:
                    override_dict[key] = {}

                sub_dict = override_dict[key]
                sub_reference = reference[key]
                path += (key,)
                sub_name = transformed_name.partition(key)[2][1:]

                opt_name_to_override(
                    sub_name, overriden_value, sub_dict, sub_reference, path)
            else:
                override_dict[key] = overriden_value
            break
    else:
        raise UnknownOption(name, path)
