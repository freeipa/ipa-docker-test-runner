IPA-Docker test runner [![Build Status](https://travis-ci.org/freeipa/ipa-docker-test-runner.svg?branch=master)](https://travis-ci.org/freeipa/ipa-docker-test-runner)
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

    pip3 install --user git+https://github.com/freeipa/ipa-docker-test-runner

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

You may specify alternative configuration file by specifying '-c/--config'
option. The values in this file will override user-wide configuration, which
in turn overrides hard-coded defaults.

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

Configuration of sub-commands
-----------------------------

`ipa-docker-test-runner` stores the configuration of the individual steps
undertaken during the run in the 'steps' subsection of the configuration file.
This allows for some degree of fine-tuning the exact workflow to suit you
particular needs. Some of the steps can re-use configuration variables from
other sections via a simple Python string templating.

The steps undertaken by `build` sub-command are the following:

* `builddep`:
  install the build dependencies missing in the Docker image (e.g. because you
  added some new ones)

* `tox`:
  run tox

* `configure`:
  run autoconf/automake to generate platform specific files and build
  directives

* `lint`:
  run pylint and jslint. This steps is skipped when `--developer-mode` is
  specified in the `build` subcommand

* `build`:
  build the target `${make_target}` specified by CLI option (rpms by default)

`install-server` sub-command uses the following:

* `install_packages`:
  install RPMS from the build step. You may change this to install from COPR
  or official repo.

* `install_server`:
  install FreeIPA server using directives from `server` subsection
  (`${server_realm}`, `${server_domain}`, etc.). Also installs additional
  components such as KRA, smb, etc.

`run-tests` runs the following:

* `prepare_tests`:
  prepare the testing infrastructure (local .ipa directory, DM passwords
  etc.). `${server_password}` is expanded in the DM/admin password specified
  in the `server` subsection.

* run-tests:
  executes `ipa-run-tests`. If `verbose` is set to true in `tests`, verbose
  output is produced. `ignore` directive is expanded via `${tests_ignore}` to
  a series of `--ignore TEST` options causing pytest to ignore the
  files/directories during discovery. `${path}` variable is expanded into any
  paths specified as arguments to `run-tests` sub-command, or into empty
  string (run everything that is not ignored)

There is one last special step, `cleanup` which is called at the end of the
run or whenever an error occurs. By default it resets the ownership of the git
repo, but you may supply some additional tasks, like cleaning untracked files
etc.

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
open an issue on https://github.com/freeipa/ipa-docker-test-runner.
Pull-requests are very welcome. 
