IPA-Docker test runner [![Build Status](https://travis-ci.org/martbab/ipa-docker-test-runner.svg?branch=master)](https://travis-ci.org/martbab/ipa-docker-test-runner)
======================

A simple and dumb tool to run [FreeIPA](https://github.com/freeipa/freeipa)
out-of-tree tests in a Docker Container. This Python script automates various
tasks required to run a FreeIPA test suite, such as:

* building RPMs from source given a git repo
* installing RPMS and a FreeIPA server against which the test will be run
* preparing the test environment
* running either all applicable tests or only a selected subset

WARNING
-------

This project uses Docker images which are meant to be used for non-persistent
testing. The handling of these images is also quite insecure and unsuitable
for production environment.

Have a look at [Jan Pazdziora's
repo](https://github.com/adelton/docker-freeipa) if you search for
production-ready images with FreeIPA server and SSSD client.

Installation
------------

You need to have python3 installed along with PyYAML and docker-py packages.
If you wish to run the included tests you need to have pytest installed as
well.

The safest way is to clone the git repo and install the package into clean
Python root using virtualenv:

    $ python3 -m venv venv
    $ venv/bin/pip install .
    $ venv/bin/ipa-docker-test-runner

You can also use pip to install `ipa-docker-test-runner` directly from github:

    pip3 install --user git+https://github.com/martbab/ipa-docker-test-runner

It is preferrable to install ipa-docker-test-runner into the local user's
PYTHONPATH in order to avoid clashes with the packages installed system-wide.
After installation you should have `ipa-docker-test-runner` script in your
$PATH.

Configuration
-------------

Run `ipa-docker-test-runner sample-config` to generate a YaML config file
(`.ipa_docker_config.yaml`) in your home directory. You should then configure
`git_repo` to point to your local copy of FreeIPA repository and `image`
directive in `container` to the image you wish to use.

See https://hub.docker.com/r/martbab/freeipa-fedora-test-runner/ for available
images (currently only one for fedora-latest, but more will be coming soon)

You can also build your own images from the Dockerfiles provided in the
project git repo.

Also make sure you have Docker daemon up and running and that you are member
of `docker` group and can thus use it without root privileges.

Usage
-----

To get help on the sub-commands, run `ipa-docker-test-runner --help`. Here are
some example usage patterns:

* build RPMs from the configured repo:

    ```
    ipa-docker-test-runner build
    ```

* Test out the FreeIPA server installation:

    ```
    ipa-docker-test-runner install-server
    ```

* Run all XMLRPC tests:

    ```
    ipa-docker-test-runner run-tests test_xmlrpc
    ```

Please note that any prerequisite(s) for a job will be run automatically: For
example, `run-tests` will first run `build` and `install-server`. This may be
changed in the future so that prerequisite steps could be skipped by option.

NOTE: apart from stopping and removing the container and chown'ing the files
in the repo from root back to the user, there is no additional cleanup
performed by the script. This is on purpose: since it is expected to be used
with a git repo, you can use `git clean -dfx` to remove all mess left behind
by build process.

Accessing the container
-----------------------

By default the created container is
automatically stopped and removed upon termination. You may use `--no-cleanup`
option to leave the container running after all commands are finished e.g. to
inspect the created environment or logs.

In this case `ipa-docker-test-runner` will print out the ID of running
container before exiting. You may then use `docker exec/attach` to access it.
E.g.:

    docker exec -ti <CONTAINER_ID> bash

starts an interactive bash session in the container.

To stop and remove container manually, run `docker stop <CONTAINER_ID> &&
docker rm <CONTAINER_ID>`.

Reporting Bugs
--------------

If you found a bug or would like to propose an enhancement, do not hesitate to
open an issue on https://github.com/martbab/ipa-docker-test-runner.
Pull-requests are very welcome. 
