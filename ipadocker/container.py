# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Class encapsulating the state and operations on an IPA container
"""

import copy
import logging


def _bind_git_repo(config):
    binds = config['host']['binds']
    git_repo = config['git_repo']
    working_dir = config['container']['working_dir']

    binds.append(':'.join([git_repo, working_dir, 'rw,Z']))


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
