# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
CLI facing part
"""

import argparse
import logging
import sys

import docker

from ipadocker import config, constants, container


DEFAULT_MAKE_TARGET = 'rpms'
DEFAULT_DEVEL_MODE = False

logger = logging.getLogger(__name__)


def setup_loggers(args):
    log_level = logging.DEBUG if args.debug else logging.INFO

    root_logger = logging.getLogger('')
    root_formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M')
    root_logger.setLevel(log_level)

    console = logging.StreamHandler()
    console.setFormatter(root_formatter)

    # exec_logger logs the output from commands executed in the container
    # that's why it has empty formatter so that only the stdout/stderr are
    # printed. Also, do not propagate the logger to upper levels
    exec_logger = logging.getLogger('.'.join([container.__name__, 'exec']))
    exec_formatter = logging.Formatter()
    exec_logger.propagate = False
    exec_console = logging.StreamHandler()
    exec_console.setFormatter(exec_formatter)

    root_logger.addHandler(console)

    if args.log_file is not None:
        log_file = logging.FileHandler(args.log_file)
        log_file.setFormatter(root_formatter)
        root_logger.addHandler(log_file)

        exec_log_file = logging.FileHandler(args.log_file)
        exec_log_file.setFormatter(exec_formatter)
        exec_logger.addHandler(exec_log_file)
    else:
        exec_logger.addHandler(exec_console)


def make_parser():
    parser = argparse.ArgumentParser(
        description="Build FreeIPA, install server "
                    "and run tests in a container")
    parser.add_argument(
        '-d',
        '--debug',
        default=False,
        action='store_true',
        help="Print out debugging info"
    )
    parser.add_argument(
        '-l',
        '--log-file',
        default=None,
        metavar="FILENAME",
        help="Log command output to a file"
    )
    parser.add_argument(
        '--no-cleanup',
        action='store_true',
        default=False,
        help="Do not stop and remove container at the end"
    )

    subcommands = parser.add_subparsers(
        dest='action_name',
    )

    build_cmd = subcommands.add_parser(
        'build',
        help='execute build in container'
    )
    build_cmd.add_argument(
        '--make-target',
        choices={'lint', 'srpms', 'rpms', 'check', 'version-update'},
        default=DEFAULT_MAKE_TARGET,
        help='make target'
    )
    build_cmd.add_argument(
        '--developer-mode',
        default=DEFAULT_DEVEL_MODE,
        action='store_true',
        help="developer mode (pylint errors during build are ignored)."
    )
    build_cmd.add_argument(
        '-b',
        '--builddep-opts',
        default=['-D "with_lint 1"'],
        action='append',
        help="options to pass to 'dnf builddep'"
    )

    subcommands.add_parser(
        'install-server',
        help='install FreeIPA server in container'
    )

    run_test_cmd = subcommands.add_parser(
        'run-tests',
        help='run tests in the container'
    )
    run_test_cmd.add_argument(
        'path',
        nargs="*",
        metavar='PATH',
        help="list of paths to execute"
    )

    subcommands.add_parser(
        'sample-config',
        help="Write sample config file into {}".format(
            constants.DEFAULT_CONFIG_FILE)
    )

    return parser


def prerequisite(*prerequisites):
    """
    This decorator marks functions that must be run successfuly before the
    decorated function is executed. Please note that these functions must
    accept the IPAContainer instance and a argparse Namespace as positional
    parameters (see `tests.test_cli` module for an illustration of how this
    works)

    :param prerequisites: functions to call before decorated is executed
    """
    def mark_prerequisite(func):
        def wrapped(docker_container, parsed_args):
            for prer_func in prerequisites:
                prer_func(docker_container, parsed_args)

            func(docker_container, parsed_args)
        return wrapped
    return mark_prerequisite


def build(docker_container, args):
    make_target = getattr(args, 'make_target', DEFAULT_MAKE_TARGET)
    developer_mode = getattr(args, 'developer_mode', DEFAULT_DEVEL_MODE)
    builddep_opts = getattr(args, 'builddep_opts', None)

    docker_container.build(
        make_target=make_target,
        developer_mode=developer_mode,
        builddep_opts=builddep_opts)


@prerequisite(build)
def install_packages(docker_container, args):
    docker_container.install_packages()


@prerequisite(install_packages)
def install_server(docker_container, args):
    docker_container.install_server()


@prerequisite(install_server)
def prepare_tests(docker_container, args):
    docker_container.prepare_tests()


@prerequisite(prepare_tests)
def run_tests(docker_container, args):
    path = getattr(args, 'path', None)

    docker_container.run_tests(path=path)


def sample_config(ipaconfig, logger):
    logger.info("Writing configuration to file %s",
                constants.DEFAULT_CONFIG_FILE)

    with open(constants.DEFAULT_CONFIG_FILE, 'w') as default_config_file:
        ipaconfig.write_config(default_config_file)


def get_action(cli_name):
    return {
        'build': build,
        'install-server': install_server,
        'run-tests': run_tests,
        'sample-config': sample_config
    }[cli_name]


def create_container(ipaconfig, args):
    try:
        docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                                      version='auto')
        return container.IPAContainer(docker_client, ipaconfig)
    except ConnectionError as e:
        logger.error("Failed to connect to Docker daemon: %s", e)
        logger.error(
            "Make sure that Docker is running and you have adequate"
            "permissions to communicate with it")
        logger.error("See 'journalctl -xe' for more details")
        raise
    except docker.errors.APIError as e:
        logger.error("Docker API returned an error: %s", e)
        raise
    except Exception as e:
        logger.error(
            "An exception has occured while connecting to Docker "
            "daemon: %s", e)
        raise


def stop_and_remove_container(container):
    try:
        container.stop_and_remove()
    except Exception as e:
        logger.warning("Cannot remove container: %s", e)


def chown_git_repo(container):
    try:
        container.chown_working_dir()
    except Exception as e:
        logger.warning("Cannot chown working directory: %s", e)


def run_action(ipaconfig, args, action):
    ipacontainer = create_container(ipaconfig, args)

    try:
        action(ipacontainer, args)
    except docker.errors.APIError as e:
        logger.error("Docker API returned an error: %s", e)
        raise
    except container.ContainerExecError as e:
        logger.error(e)
        raise
    except Exception as e:
        logger.error("An exception has occured when running command: %s", e)
        raise
    finally:
        chown_git_repo(ipacontainer)
        if args.no_cleanup:
            logger.info("Container cleanup suppressed.")
            logger.info(
                "You can access and inspect the container using ID: %s",
                ipacontainer.container_id)
            logger.info("You will have to stop and remove it manually")
            return

        stop_and_remove_container(ipacontainer)


def main():
    argparser = make_parser()

    args = argparser.parse_args()
    if args.action_name is None:
        sys.exit(argparser.print_usage())

    setup_loggers(args)

    logger.debug("Argument namespace: %s", args)
    logger.info("Starting %s", sys.argv[0])
    logger.info("Reading configuration")

    try:
        ipaconfig = config.IPADockerConfig()
    except ValueError as e:
        logger.error("Failed to read configuration: %s", e)
        sys.exit(1)

    action = get_action(args.action_name)
    if action is sample_config:
        sample_config(ipaconfig, logger)
        sys.exit(0)

    try:
        run_action(ipaconfig, args, action)
    except container.ContainerExecError as e:
        sys.exit(e.exit_code)
    except Exception as e:
        logger.debug(e, exc_info=e)
        sys.exit(2)

    logger.info("%s finished succesfully.", sys.argv[0])

if __name__ == '__main__':
    main()
