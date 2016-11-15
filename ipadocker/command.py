# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
The command execution engine
"""

import logging

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

    :returns: The exit code of command upon completion
    """

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
