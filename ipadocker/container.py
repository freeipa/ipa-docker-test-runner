# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Class encapsulating the state and operations on an IPA container
"""

import copy
import itertools
import logging
import os

import docker

from ipadocker import config


class ContainerExecError(Exception):
    """
    Exception raised when the command execution inside the container fails

    :param cmd: the command that failed
    :param exit_code: the returned exit code (default: 1)
    """
    def __init__(self, cmd, exit_code=1):
        self.exit_code = exit_code
        msg = "Command {} failed (exit code {})".format(cmd, exit_code)

        super(ContainerExecError, self).__init__(msg)


def _bind_git_repo(config):
    binds = config['host']['binds']
    git_repo = config['git_repo']
    working_dir = config['container']['working_dir']

    binds.append(':'.join([git_repo, working_dir, 'rw,Z']))


def exec_command(docker_client, container_id, cmd):
    """
    Execute a command in running container. A small wrapper around
    `exec_create` and `exec_start` methods. The command is run inside a spawned
    bash session

    :param docker_client: Docker Client API instance
    :param container_id: ID of the running container
    :param cmd: Command to run, either string or list

    :returns: The exit code of command upon completion
    """
    logger = logging.getLogger('.'.join([__name__, 'exec']))

    if not isinstance(cmd, str):
        command = ' '.join(cmd)
    else:
        command = cmd

    bash_command = "bash -c '{}'".format(command)

    exec_id = docker_client.exec_create(container_id, cmd=bash_command)

    for output in docker_client.exec_start(exec_id, stream=True):
        logger.info(output.decode().rstrip())

    exec_status = docker_client.exec_inspect(exec_id)
    return exec_status["ExitCode"]


def create_container(docker_client, config, logger):
    """
    Create container. If the image specified from the passed in config is not
    found, it will be pulled from Docker hub.

    :param docker_client: Instance of Docker client
    :param config: instance of IPADockerConfig
    :param logger: logger instance
    """

    image = config['container']['image']
    logger.info(
        "Creating container from %s", image)

    try:
        result = docker_client.create_container(
            host_config=docker_client.create_host_config(
                **config['host']),
            **config['container'])
    except docker.errors.NotFound:
        logger.info("Image %s not found locally, trying pull...", image)
        logger.info("This may take a few minutes.")
        output = docker_client.pull(image)
        logger.debug(output)

        logger.info("Image pulled in successfuly.")

        result = docker_client.create_container(
            host_config=docker_client.create_host_config(
                **config['host']),
            **config['container'])

    return result['Id']


class IPAContainer:
    """
    Class which encapsulates the creation and manipulation of a Docker
    container. The configuration is passed as a IPADockerConfig instance (see
    `ipadocker.config` module)

    :param docker_client: Docker Client API instance
    :param config: IPADockerConfig instance
    """

    def __init__(self, docker_client, config):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.docker_client = docker_client

        # create a deep copy of the config. We want to add git repo to binds
        # without changing the format of original config
        self.config = copy.deepcopy(config)
        _bind_git_repo(self.config)

        self.logger.info(
            "Creating container from %s", self.config['container']['image'])

        self.container_id = create_container(
            self.docker_client, self.config, self.logger)

        self.logger.info("SUCCESS")

        self.logger.info("Starting container ID: %s", self.container_id)
        response = self.docker_client.start(container=self.container_id)
        self.logger.debug("API response: %s", response)

    @property
    def status(self):
        """
        Return container status (Running, Dead, etc.)
        """
        return self.docker_client.inspect_container(
            self.container_id)['State']['Status']

    def exec_command(self, cmd):
        """
        Execute a command in container

        :param cmd: Command to run, can be string or list/tuple

        :raises: ContainerExecError when the process exists with non-zero
        status
        """
        self.logger.info("Executing command: %s", cmd)

        exit_code = exec_command(self.docker_client, self.container_id, cmd)

        if exit_code:
            raise ContainerExecError(cmd, exit_code)

    def build(self, make_target='rpms', developer_mode=False,
              builddep_opts=None):
        """
        Build FreeIPA packages, i.e. run `make rpms` by default

        :param make_target: custom target for make, e.g. `lint`
        :param developer_mode: Ignore pylint errors (sets DEVELOPER_MODE
        :param builddep_opts: If not None, a list of options to pass to `dnf
            builddep`
        environment variable to 1)
        """
        build_cmd = ['make', make_target]

        if developer_mode:
            build_cmd.insert(0, 'DEVELOPER_MODE=1')

        builddep_cmd = ['dnf', 'builddep', '-y']
        if builddep_opts is not None:
            builddep_cmd.extend(builddep_opts)

        builddep_cmd.extend(['--spec', 'freeipa.spec.in'])

        self.exec_command(builddep_cmd)
        self.exec_command(build_cmd)

    def install_packages(self):
        """
        Install RPM packages from working_dir/dist/rpms directory
        """
        rpms_path = os.path.join(
            self.config['container']['working_dir'], 'dist', 'rpms', '*.rpm')
        cmd = 'dnf install -y {}'.format(rpms_path)

        self.exec_command(cmd)

    def install_server(self):
        """
        Install FreeIPA server and KRA inside the container.
        """
        domain = self.config['server']['domain']
        realm = domain.upper()
        password = self.config['server']['password']
        setup_dns = self.config['server']['setup_dns']

        cmd = ['ipa-server-install', '-U', '--domain', domain, '--realm',
               realm, '-p', password, '-a', password, '--auto-forwarders']

        if setup_dns:
            cmd.append('--setup-dns')

        self.exec_command(cmd)
        self.exec_command('ipa-kra-install -p {}'.format(password))

    def prepare_tests(self):
        """
        prepare for running out-of-tree tests inside the container:
            * create /root/.ipa directory and copy files from /etc/ipa/ there
            * kinit as admin
            * store directory manager password in /etc/.ipa/.dmpw (needed for
              some Backend tests)
        """
        password = self.config['server']['password']
        self.exec_command(
            'echo {} | kinit admin && ipa ping'.format(password))

        self.exec_command('cp -r /etc/ipa/* /root/.ipa/.')
        self.exec_command('echo {} > /root/.ipa/.dmpw'.format(password))

    def run_tests(self, path=None):
        """
        Run out-of-tree tests. Integration tests will be skipped

        :param path: list of paths to execute (default: None, that means
        discovers all tests in `ipatests` directory)
        """
        cmd = ['ipa-run-tests']
        cmd.extend(config.get_ipa_run_tests_options(self.config))

        if path is not None:
            cmd.extend(path)

        self.exec_command(cmd)

    def chown_working_dir(self):
        """
        Recursively set the owner of the working directory back to the user
        """
        cmd = 'chown -R {}:{} {}'.format(
            os.getuid(),
            os.getgid(),
            self.config['container']['working_dir'])

        self.exec_command(cmd)

    def stop(self):
        """
        Stop the running container
        """
        self.docker_client.stop(self.container_id)

    def remove(self):
        """
        Remove the container
        """
        self.docker_client.remove_container(self.container_id)

    def stop_and_remove(self):
        """
        Convenience method that stops and removes running container
        """
        self.stop()
        self.remove()
