# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
The command execution engine
"""

import logging
import string

logger = logging.getLogger(__name__)


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


def exec_command(docker_client, container_id, cmd):
    """
    Execute a command in running container. A small wrapper around
    `exec_create` and `exec_start` methods. The command is run inside a spawned
    bash session

    :param docker_client: Docker Client API instance
    :param container_id: ID of the running container
    :param cmd: Command to run, either string or list

    :raises: ContainerExecError if the command failed for some reason
    """
    exec_logger = logging.getLogger('.'.join([__name__, 'exec']))

    if not isinstance(cmd, str):
        command = ' '.join(cmd)
    else:
        command = cmd

    bash_command = "bash -c '{}'".format(command.replace("'", "'\\''"))

    exec_id = docker_client.exec_create(container_id, cmd=bash_command)

    for output in docker_client.exec_start(exec_id, stream=True):
        exec_logger.info(output.decode().rstrip())

    exec_status = docker_client.exec_inspect(exec_id)
    exit_code = exec_status["ExitCode"]

    if exit_code:
        raise ContainerExecError(cmd, exit_code)


class ExecutionStep:
    """
    A single step of execution in the container

    :param commands: list of command string to execute, including interpolation
        variables
    :param template_mapping: a mapping containing key-value pairs to substitute
        into the command strings
    :param kwargs: additional keyword arguments for the template substitution

    the keyword arguments take precedence over the values in the mapping as is
    expected for the Template string engine
    """
    def __init__(self, commands, template_mapping, **kwargs):
        self.commands = []

        for command in commands:
            logger.debug("Command before substitution: %s", command)
            cmd_template = string.Template(command)
            self.commands.append(
                cmd_template.substitute(template_mapping, **kwargs)
            )

    def __call__(self, container):
        """
        Execute the commands in container

        :params container: the IPAContainer instance holding container info

        :raises: ContainerExecError when the process exists with non-zero
        status
        """
        container_id = container.container_id
        docker_client = container.docker_client

        for cmd in self.commands:
            logger.info("Executing command: %s", cmd)
            exec_command(docker_client, container_id, cmd)
