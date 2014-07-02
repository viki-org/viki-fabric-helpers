import os
import shutil
import sys
import tempfile

import viki.fabric.helpers as viki_fab_helpers

from fabric.api import env
from fabric.colors import blue, red, yellow
from fabric.context_managers import lcd
from fabric.decorators import runs_once, task
from fabric.operations import local, run
from fabric.tasks import execute

def construct_tagged_docker_image_name(dockerImageName, dockerImageTag=None):
  """Constructs a tagged docker image name from a Docker image name and an
  optional tag.

  Args:
    dockerImageName(str): Name of the Docker image in `namespace/image` format

    dockerImageTag(str, optional): Optional tag of the Docker image
  """
  if dockerImageTag is None:
    return dockerImageName
  else:
    return "{}:{}".format(dockerImageName, dockerImageTag)

@runs_once
@task
def build_docker_image_from_git_repo(gitRepository, dockerImageName,
    branch="master", runGitCryptInit=False, gitCryptKeyPath=None,
    relativeDockerfileDirInGitRepo=".", dockerImageTag=None):
  """A _local_ task which does the following:

  1. clones a given git repository to a local temporary directory and checks out
  the branch supplied

  2. If the `performGitCryptInit` argument is `True`, runs `git-crypt init` to
  decrypt the files

  3. builds a Docker image using the Dockerfile in the
  `relativeDockerfileDirInGitRepo` directory of the git repository.
  The Docker image is tagged (details are in the docstring for the
  `dockerImageTag` parameter).

  NOTE: This task is only run once regardless of the number of hosts/roles you
  supply.

  Args:
    gitRepository(str): The git repository to clone; this repository will be
      supplied to `git clone`

    dockerImageName(str): Name of the Docker image in `namespace/image` format

    branch(str, optional): The git branch of this repository we wish to build
      the Docker image from

    runGitCryptInit(bool, optional): If `True`, runs `git-crypt init` using
      the key specified by the `gitCryptKeyPath` parameter

    gitCryptKeyPath(str, optional): Path to the git-crypt key for the
      repository; this must be given an existing path if the `runGitCryptInit`
      parameter is set to `True`

    relativeDockerfileDirInGitRepo(str, optional): the directory inside the git
      repository that houses the Dockerfile we will be using to build the Docker
      image; this should be a path relative to the git repository. For instance,
      if the `base-image` directory within the git repository holds the
      Dockerfile we want to build, the `relativeDockerfileDirInGitRepo`
      parameter should be set to the string "base-image". Defaults to "." (the
      top level of the git repository).

    dockerImageTag(str, optional): If supplied, the Docker image is tagged with
      it. Otherwise, a generated tag in the format
      `branch-first 12 digits in HEAD commit SHA1` is used. For instance, if
      `dockerImageTag` is not supplied, `branch` is "master" and its commit SHA1
      is 18f450dc8c4be916fdf7f47cf79aae9af1a67cd7, then the tag will be
      `master-18f450dc8c4b`.

  Returns:
    str: The tag of the Docker image

  Raises:
    ValueError: if `runGitCryptInit` is True, and either:
      - the `gitCryptKeyPath` parameter is not given, or `None` is supplied
      - the `gitCryptKeyPath` parameter is a non-existent path
  """
  if runGitCryptInit:
    # Check validity of `gitCryptKeyPath` because `runGitCryptInit` is True
    if gitCryptKeyPath is None:
      raise ValueError(
        "`gitCryptKeyPath` parameter given is `None`; since runGitCryptInit is"
        " `True`, please supply the path to a git-crypt key"
      )
    elif not os.path.exists(gitCryptKeyPath):
      raise ValueError(
        ("`gitCryptKeyPath` parameter is a non-existent file `{}`. Please "
        "  supply a path to an existing git-crypt key.").format(gitCryptKeyPath)
      )

  # Clone this git repository into a temporary directory so we can check out
  # the branch from which we want to build the Docker image
  tmpGitRepoPathName = tempfile.mkdtemp()
  local("git clone {} {}".format(gitRepository, tmpGitRepoPathName))
  # we place the `dockerImageTag` variable here to mutate it inside the `with`
  dockerImageTag = None
  # go into the cloned repo
  with lcd(tmpGitRepoPathName):
    # check out the branch, set up git-crypt to decrypt the encrypted files (if
    # instructed).
    local("git checkout {}".format(branch))
    if runGitCryptInit:
      local("git-crypt init {}".format(gitCryptKeyPath))

    # Obtain the HEAD commit's SHA1
    headSHA1 = local("git rev-parse HEAD", capture=True).stdout
    # When the user did not supply the `dockerImageTag` argument
    if dockerImageTag is None:
      # Construct the tag in the following format:
      #
      #     `{branch}-{first 12 characters of commit SHA1}`
      #
      # and assign it to `dockerImageTag`
      dockerImageTag = "{}-{}".format(branch, headSHA1[:12])
    dockerTaggedImageName = construct_tagged_docker_image_name(dockerImageName,
      dockerImageTag
    )
    print(blue(
      "Building `{}` Docker image from branch `{}` commit `{}`...".format(
        dockerTaggedImageName, branch, headSHA1
      )
    ))
    # Build the tagged Docker image using the Dockerfile in the
    # `relativeDockerfileInGitRepo` directory inside the Git repository
    local("docker build -t {} {}".format(dockerTaggedImageName,
      relativeDockerfileDirInGitRepo
    ))

  # delete temporary git repo directory
  shutil.rmtree(tmpGitRepoPathName)
  return dockerImageTag

@runs_once
@task
def push_docker_image_to_registry(dockerImageName, dockerImageTag="latest"):
  """A _local_ task which pushes a local Docker image with a given tag to the
  Docker registry (http://index.docker.io).

  Args:
    dockerImageName(str): Name of the Docker image in `namespace/image` format

    dockerImageTag(str, optional): Tag of the Docker image, defaults to the
      string "latest"
  """
  dockerTaggedImageName = construct_tagged_docker_image_name(dockerImageName,
    dockerImageTag)
  print(yellow(
    ("Pushing image `{}` to the Docker registry (http://index.docker.io).\n"
     "Please login to continue.").format(dockerTaggedImageName)
  ))
  # login to Docker registry and push the tagged Docker image we just built
  local("docker login")
  local("docker push {}".format(dockerTaggedImageName))

@runs_once
@task
def build_docker_image_from_git_repo_and_push_to_registry(gitRepository,
    dockerImageName, **kwargs):
  """A _local_ task which builds a Docker image from a git repository and
  pushes it to the Docker registry (http://index.docker.io). This task runs the
  `build_docker_image_from_git_repo` followed by the
  `push_docker_image_to_registry` task.

  Args:
    gitRepository(str): Refer to the docstring for the same parameter in
      `build_docker_image_from_git_repo` Fabric task

    dockerImageName(str): Refer to the docstring for the same parameter in the
      `build_docker_image_from_git_repo` Fabric task

    \*\*kwargs: Keyword arguments passed to the `build_docker_image_from_git_repo`
      Fabric task

  Returns:
    str: The tag of the built Docker image
  """
  retVal = execute(build_docker_image_from_git_repo, gitRepository,
    dockerImageName, roles=env.roles, hosts=env.hosts, **kwargs
  )
  dockerImageTag = \
    viki_fab_helpers.get_return_value_from_result_of_execute_runs_once(retVal)
  execute(push_docker_image_to_registry, dockerImageName,
    dockerImageTag=dockerImageTag, roles=env.roles, hosts=env.hosts
  )
  return dockerImageTag

@task
def pull_docker_image_from_registry(dockerImageName,
    dockerImageTag="latest"):
  """Pulls a tagged Docker image from the Docker registry.

  Rationale: While a `docker run` command for a missing image will pull the
  image from the Docker registry, it requires any running Docker container with
  the same name to be stopped before the newly pulled Docker container
  eventually runs. This usually means stopping any running Docker container
  with the same name before a time consuming `docker pull`. Pulling the desired
  Docker image before a `docker stop` `docker run` will minimize the downtime
  of the Docker container.

  Args:
    dockerImageName(str): Name of the Docker image in `namespace/image` format

    dockerImageTag(str, optional): Tag of the Docker image to pull, defaults to
      the string `latest`
  """
  dockerTaggedImageName = construct_tagged_docker_image_name(dockerImageName,
    dockerImageTag
  )
  print(yellow(
    ("Pulling `{}` from the Docker registry (http://index.docker.io)\n"
     "Please login to continue.").format(dockerTaggedImageName)
  ))
  run("docker login")
  run("docker pull {}".format(dockerTaggedImageName))
