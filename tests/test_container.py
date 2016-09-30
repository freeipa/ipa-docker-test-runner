# Author: Martin Babinsky <martbab@gmail.com>
# See LICENSE file for license

"""
Test suite for IPAContainer() initialization
"""


import docker
import pytest

from ipadocker import config, container


@pytest.fixture()
def docker_client():
    """
    Docker API client. Set version to auto to always use server version
    """
    return docker.Client(base_url='unix://var/run/docker.sock', version='auto')


@pytest.yield_fixture()
def ipacontainer(docker_client):
    """
    Instantiate the container. This should pull the image from registry and
    create container. Stop and remove the container at the end.
    """
    docker_config = config.IPADockerConfig()
    docker_container = container.IPAContainer(docker_client, docker_config)

    try:
        yield docker_container
    finally:
        try:
            docker_container.stop_and_remove()
        except Exception:
            pass


def test_container_init(ipacontainer):
    """
    Initialize the container and check that it has 'running' status
    """
    assert ipacontainer.status == u'running'
