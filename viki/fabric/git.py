import functools
import os.path
import yaml

import viki.fabric.helpers as fabric_helpers

from fabric.api import env, run, task
from fabric.colors import red
from fabric.context_managers import hide, settings
from fabric.contrib.files import exists, upload_template
from fabric.operations import local
from viki.fabric import VIKI_FABRIC_CONFIG_KEY_NAME
from viki.fabric.helpers import env_has_nested_keys, get_in_viki_fabric_config

# Whether the `_initialize` function has been called
_INITIALIZED = False

# Name of the ssh private key that allows us to clone private analytics Github
# repositories
_SSH_PRIVATE_KEY = None

# Public key for the above private key
_SSH_PUBLIC_KEY = None

# Directory name on the server (under $HOME) where the `_SSH_PRIVATE_KEY` and
# `_SSH_PUBLIC_KEY` files are stored
_SSH_KEYS_DIR = None

# Local directory where the `_SSH_PRIVATE_KEY` and `_SSH_PUBLIC_KEY` are stored
_SSH_KEYS_LOCAL_COPY_DIR = None

# Folder storing template for `_GIT_SSH_SCRIPT_NAME`
_GIT_SSH_SCRIPT_LOCAL_FOLDER = None

# Script to use like this:
#
#     GIT_SSH=$HOME/scriptname git operation args
#
# Concrete example:
#
#     GIT_SSH=$HOME/gitwrap.sh git fetch origin
#
# This is for cloning from secret repositories, and makes use of the
# `_SSH_PRIVATE_KEY`
_GIT_SSH_SCRIPT_NAME = None

def _initialize():
  """Initializes some global variables in this module with those read from the
  `viki_fabric_config.yml` file (and subsequently stored into
  `env.viki_fabric_config["viki.fabric.git"]`).
  """
  global _INITIALIZED
  if _INITIALIZED:
    return

  if not env_has_nested_keys([VIKI_FABRIC_CONFIG_KEY_NAME, "viki.fabric.git"]):
    raise RuntimeError(
      "For modules importing the `viki.fabric.git` module (directly or"
      " indirectly), a `viki_fabric_config.yml` containing a `viki.fabric.git`"
      " key (whose value is a dict) is required at the directory where the main"
      " Python script is run.\n"
      "For more information, consult the documentation at"
      " http://viki-fabric-helpers.readthedocs.org/en/latest/viki-fabric-git.html"
    )

  # Keys we expect to be in env[VIKI_FABRIC_CONFIG_KEY_NAME]["viki.fabric.git"]
  expectedKeys = ["ssh_private_key", "ssh_public_key",
    "ssh_keys_local_copy_dir", "ssh_keys_dir", "git_ssh_script_name",
    "git_ssh_script_local_folder"
  ]
  # obtain env[VIKI_FABRIC_CONFIG_KEY_NAME]["viki.fabric.git"]
  vikiFabricGitConfig = get_in_viki_fabric_config(["viki.fabric.git"])
  assert(isinstance(vikiFabricGitConfig, dict))
  # check that the `expectedKeys` exist
  for k in expectedKeys:
    assert(k in vikiFabricGitConfig)

  # assign them to global variables for convenience
  global _SSH_PRIVATE_KEY, _SSH_PUBLIC_KEY, _SSH_KEYS_LOCAL_COPY_DIR, \
         _SSH_KEYS_DIR, _GIT_SSH_SCRIPT_LOCAL_FOLDER, _GIT_SSH_SCRIPT_NAME
  _SSH_PRIVATE_KEY = vikiFabricGitConfig["ssh_private_key"]
  _SSH_PUBLIC_KEY = vikiFabricGitConfig["ssh_public_key"]
  _SSH_KEYS_LOCAL_COPY_DIR = vikiFabricGitConfig["ssh_keys_local_copy_dir"]
  _SSH_KEYS_DIR = vikiFabricGitConfig["ssh_keys_dir"]
  _GIT_SSH_SCRIPT_NAME = vikiFabricGitConfig["git_ssh_script_name"]
  _GIT_SSH_SCRIPT_LOCAL_FOLDER = \
    vikiFabricGitConfig["git_ssh_script_local_folder"]

  _INITIALIZED = True

def _check_initialized(f):
  """A decorator which checks that the `_initialize` function has been called;
  if not, it calls the `_initialize` function, followed by the wrapped function`
  """
  @functools.wraps(f)
  def wrapper(*args, **kwargs):
    _initialize()
    return f(*args, **kwargs)
  return wrapper

# Determines if a directory is under git control
def is_dir_under_git_control(dirName):
  """Determines if a directory on a server is under Git control.

  Args:
    dirName(str): directory name on the server for which we wish to determine
      whether it's under Git control

  Returns:
    bool: True if the directory on the server is under Git control, False
      otherwise.

  >>> is_dir_under_git_control("/home/ubuntu/viki-fabric-helpers")
  True
  """
  gitRevParseCmd = "cd {} && git rev-parse --git-dir".format(dirName)
  with settings(hide("warnings", "stdout", "stderr"), warn_only=True):
    return run(gitRevParseCmd).succeeded

@task
@_check_initialized
def setup_server_for_git_clone(homeDir=None):
  """Fabric task that sets up the ssh keys and a wrapper script for GIT_SSH
  to allow cloning of private Github repositories.

  Args:
    homeDir(str, optional): home directory for the server. If not supplied or if
      `None` is supplied, the return value of the `fabric_helpers.get_home_dir`
      function is used

  For a Python Fabric script that imports the `viki.fabric.git` module using::

      import viki.fabric.git

  we can use this Fabric task from the command line, like so::

      fab -H host1,host2,host3 viki.fabric.git.setup_server_for_git_clone

  Alternatively, for a Python Fabric script that imports the `viki.fabric.git`
  module using::

      import viki.fabric.git as fabric_git

  we can use this Fabric task from the command like, like so::

      fab -H host1,host2,host3 fabric_git.setup_server_for_git_clone

  This function can also be called as a normal function (hopefully from within
  another Fabric task).
  """
  if homeDir is None:
    homeDir = fabric_helpers.get_home_dir()
  serverName = env.host
  serverPublicKeyPath = os.path.join(homeDir, _SSH_KEYS_DIR, _SSH_PUBLIC_KEY)
  serverPrivateKeyPath = os.path.join(homeDir, _SSH_KEYS_DIR, _SSH_PRIVATE_KEY)
  localPublicKey = os.path.join(_SSH_KEYS_LOCAL_COPY_DIR, _SSH_PUBLIC_KEY)
  localPrivateKey = os.path.join(_SSH_KEYS_LOCAL_COPY_DIR, _SSH_PRIVATE_KEY)
  fabric_helpers.copy_file_to_server_if_not_exists(localPublicKey,
    serverPublicKeyPath
  )
  fabric_helpers.copy_file_to_server_if_not_exists(localPrivateKey,
    serverPrivateKeyPath
  )
  # Copy gitwrap.sh, which is a wrapper that forces `git clone` to make use of
  # the ssh private key we just copied
  gitSSHWrapperPath = get_git_ssh_script_path(homeDir)
  if not exists(gitSSHWrapperPath):
    upload_template(_GIT_SSH_SCRIPT_NAME, gitSSHWrapperPath, use_jinja=True,
      template_dir=_GIT_SSH_SCRIPT_LOCAL_FOLDER, mode=0755,
      context={ 'ssh_private_key_path': serverPrivateKeyPath }
    )

def is_fabtask_setup_server_for_git_clone_run(homeDir=None, printWarnings=True):
  """Determines if the `setup_server_for_git_clone` Fabric task has been run.

  This task checks for the existence of some files on the server to determine
  whether the `setup_server_for_git_clone` task has been run.

  Args:
    homeDir(str, optional): home directory for the server. If not supplied or if
      `None` is supplied, the return value of the `fabric_helpers.get_home_dir`
      function is used
    printWarnings(boolean): true if the `setup_server_for_git_clone` task has
      been run, false otherwise.

  Returns:
    bool: True if the `setup_server_for_git_clone` Fabric task has been run for
      the current server, False otherwise.

  >>> is_fabtask_setup_server_for_git_clone_run()
  False # along with some other output before this return value
  """
  serverName = env.host
  if homeDir is None:
    homeDir = fabric_helpers.get_home_dir()
  gitsshWrapper = get_git_ssh_script_path(homeDir)
  taskHasRun = True
  if not exists(gitsshWrapper):
    taskHasRun = False
    if printWarnings:
      print(red('`{}` does not exist on `{}`'.format(
        gitsshWrapper, serverName
      )))
  sshPublicKeyPath = _get_ssh_public_key_path(homeDir)
  if not exists(sshPublicKeyPath):
    taskHasRun = False
    if printWarnings:
      print(red('`{}` does not exist on `{}`'.format(sshPublicKeyPath,
        serverName
      )))
  sshPrivateKeyPath = _get_ssh_private_key_path(homeDir)
  if not exists(sshPrivateKeyPath):
    taskhasRun = False
    if printWarnings:
      print(red('`{}` does not exist on `{}`'.format(sshPrivateKeyPath,
        serverName
      )))
  if (not taskHasRun) and printWarnings:
    print(red((
      'Please run the `setup_server_for_git_clone` fabric task for `{}` '
      'and try again.'
    ).format(serverName)))
  return taskHasRun

@_check_initialized
def get_git_ssh_script_path(homeDir=None):
  """Returns the path to the git ssh script

  Args:
    homeDir(str, optional): home directory for the server. If not supplied or if
      `None` is supplied, the return value of the `fabric_helpers.get_home_dir`
      function is used

  Returns:
    str: the path to the git ssh script

  >>> get_git_ssh_script_path()
  "/home/ubuntu/git_ssh_wrap.sh"
  """
  if homeDir is None:
    homeDir = fabric_helpers.get_home_dir()
  return os.path.join(homeDir, _GIT_SSH_SCRIPT_NAME)

@_check_initialized
def _get_ssh_public_key_path(homeDir=None):
  """Returns the path to the Viki Analytics SSH public key

  Args:
    homeDir(str, optional): home directory for the server. If not supplied or if
      `None` is supplied, the return value of the `fabric_helpers.get_home_dir`
      function is used

  Returns:
    str: the path to the Viki Analytics SSH public key
  """
  if homeDir is None:
    homeDir = fabric_helpers.get_home_dir()
  return os.path.join(homeDir, _SSH_KEYS_DIR, _SSH_PUBLIC_KEY)

@_check_initialized
def _get_ssh_private_key_path(homeDir=None):
  """Returns the path to the Viki Analytics SSH private key

  Args:
    homeDir(str, optional): home directory for the server. If not supplied or if
      `None` is supplied, the return value of the `fabric_helpers.get_home_dir`
      function is used

  Returns:
    str: the path to the Viki Analytics SSH private key
  """
  if homeDir is None:
    homeDir = fabric_helpers.get_home_dir()
  return os.path.join(homeDir, _SSH_KEYS_DIR, _SSH_PRIVATE_KEY)

def local_git_branch_exists(branch):
  """Determines if a branch exists in the current git repository on your local
  machine.

  **NOTE:** The current working directory is assumed to be inside the git
  repository of interest.

  Args:
    branch(str): Name of the branch

  Returns:
    bool: True if the given branch exists, False otherwise

  >>> local_git_branch_exists("master")
  True
  >>> local_git_branch_exists("non_existent_branch")
  False
  """
  with settings(warn_only=True):
    return local("git show-ref --verify --quiet refs/heads/{}".format(
      branch
    )).succeeded
