`viki.fabric.docker` - A short guide
====================================

The `viki.fabric.docker` module contains several Docker related Fabric tasks
that may help reduce the effort required for writing Fabric tasks that involve
`Docker <http://www.docker.com>`_.

We will be going through an example of writing a Fabric script that builds a
Docker image on your local machine, pushes it to the Docker registry, followed
by pulling it on a set of servers. There is extensive inline documentation to
aid your understanding.

Example Script
--------------

**NOTE:** This script assumes usage of `Fabric <http://www.fabfile.org>`_
**1.9.0**. However, a version of Fabric relatively close to that *should* work
as well.

.. code-block:: python

    # the module where the functions we're covering resides
    import viki.fabric.docker as viki_docker
    # other helper functions that we'll be needing
    import viki.fabric.helpers as fab_helpers

    # Fabric library imports
    from fabric.api import env
    from fabric.decorators import runs_once, task
    from fabric.operations import run
    from fabric.tasks import execute

    # Fabric roles
    env.roledefs = {
      "production": ["m01.prod1", "m02.prod1", "m03.prod1"],
      "testing": ["t01.test1", "t02.test1", "t03.test1"]
    }

    # This Fabric task is decorated with `fabric.decorators.runs_once` because
    # it uses `fabric.tasks.execute` to run other Fabric tasks.
    #
    # Not decorating it with the `fabric.decorators.runs_once` will result in
    # the following scenario:
    #
    #     We run a Fabric task T1 on servers S1, S2 and S3.
    #     Fabric task T1 calls two other Fabric tasks T2 and T3.
    #     Fabric task T1 is not decorated with `fabric.decorators.runs_once`.
    #
    #     What happens:
    #
    #         S1 runs T1
    #             S1 runs T2
    #             S2 runs T2
    #             S3 runs T2
    #             S1 runs T3
    #             S2 runs T3
    #             S3 runs T3
    #         S2 runs T1
    #             S1 runs T2
    #             S2 runs T2
    #             S3 runs T2
    #             S1 runs T3
    #             S2 runs T3
    #             S3 runs T3
    #         S3 runs T1
    #             S1 runs T2
    #             S2 runs T2
    #             S3 runs T2
    #             S1 runs T3
    #             S2 runs T3
    #             S3 runs T3
    @runs_once
    @task
    def build_my_repo_docker_image_and_push_to_registry():
      """Fabric task which builds a Docker image for my repository and pushes
      it to the Docker registry (http://index.docker.io).
      """
      # name of the Docker image in namespace/image format
      dockerImageName = "steveJackson/myRepo"

      # Use the `fabric.tasks.execute` function to run the
      # `viki.fabric.docker.build_and_push_docker_image` Fabric task.
      # The `viki.fabric.docker.build_and_push_docker_image` Fabric task is only
      # executed once regardless of the number of hosts or roles you pass to the
      # `build_my_repo_docker_image_and_push_to_registry` task that we're
      # writing now
      retVal = execute(viki_docker.build_and_push_docker_image,
        # path to the git repository; anything that `git clone` accepts is
        # acceptable
        "https://github.com/steve-jackson/my-repo.git",

        # name of the Docker image
        dockerImageName,

        # use `git-crypt` (https://github.com/AGWA/git-crypt) to decrypt the
        # git-crypt'ed files in the cloned repository
        runGitCryptInit=True,

        # Path to the git-crypt key used for the repository
        gitCryptKeyPath="/home/steve/my-repo-gitcrypt-key",

        # the Dockerfile is located inside the `docker-build` directory of the
        # cloned repository
        relativeDockerfileDirInGitRepo="docker-build",

        # pass in the hosts and roles supplied to the
        # `build_my_repo_docker_image_and_push_to_registry` task to the
        # `viki.fabric.docker.build_and_push_docker_image` task
        hosts=env.hosts, roles=env.roles
      )

      # We did not supply the `dockerImageTag` keyword argument to the
      # above execute, hence we will need the tag of the newly built Docker
      # image, which is the return value of the task.
      #
      # However, we're using `fabric.tasks.execute`, which collects the return
      # value of all hosts into a dict whose keys are the host strings and the
      # whose values are the return values of the original task for the hosts.
      #
      # Since the `viki.fabric.docker.build_and_push_docker_image` Fabric task
      # is a local Fabric task which runs once, its return value will be the
      # same for all given hosts.
      # The `viki.fabric.helpers.get_return_value_from_result_of_execute_runs_once`
      # function is a convenience function to extract a return value from the
      # dict returned by `fabric.tasks.execute`.
      dockerImageTag = \
        fab_helpers.get_return_value_from_result_of_execute_runs_once(retVal)

      # On each given server, pull the newly built Docker image.
      # This is run once for each server.
      execute(viki_docker.pull_docker_image_from_registry,
        # name of the Docker image in `namespace/image` format
        dockerImageName,

        # tag of the Docker image; we obtained this above
        dockerImageTag=dockerImageTag,

        # pass in the hosts and roles given to the
        # `build_my_repo_docker_image_and_push_to_registry` task
        hosts=env.hosts, roles=env.roles
      )

Suppose the above script is named `fabfile.py`. To run it for the production
machines:

.. code-block:: bash

    fab -R production build_my_repo_docker_image_and_push_to_registry
