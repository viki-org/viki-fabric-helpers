import os.path
import yaml

import viki.fabric.helpers as fabric_helpers

from fabric.api import env, run, task
from fabric.colors import red
from fabric.context_managers import hide, settings
from fabric.contrib.files import exists, upload_template

# Name of the ssh private key that allows us to clone private analytics Github
# repositories
SSH_PRIVATE_KEY = None

# Public key for the above private key
SSH_PUBLIC_KEY = None

# Directory name on the server (under $HOME) where the `SSH_PRIVATE_KEY` and
# `SSH_PUBLIC_KEY` files are stored
SSH_KEYS_DIR = None

# Local directory where the `SSH_PRIVATE_KEY` and `SSH_PUBLIC_KEY` are stored
SSH_KEYS_LOCAL_COPY_DIR = None

# Folder storing template for `GIT_SSH_SCRIPT_NAME`
GIT_SSH_SCRIPT_LOCAL_FOLDER = None

# Script to use like this:
#
#     GIT_SSH=$HOME/scriptname git operation args
#
# Concrete example:
#
#     GIT_SSH=$HOME/gitwrap.sh git fetch origin
#
# This is for cloning from secret repositories, and makes use of the
# `SSH_PRIVATE_KEY`
GIT_SSH_SCRIPT_NAME = None

def initialize(yamlConfigFile):
  """Initializes globals in this module. This function should be called before
  using any public functions defined in this module.

  Args:
    yamlConfigFile(str): path to the YAML configuration file to read the
      configuration from.
  """
  with open(yamlConfigFile, "r") as f:
    yamlConfig = yaml.load(f.read())
    global SSH_PRIVATE_KEY, SSH_PUBLIC_KEY, SSH_KEYS_LOCAL_COPY_DIR, \
           SSH_KEYS_DIR, GIT_SSH_SCRIPT_FOLDER, GIT_SSH_SCRIPT_NAME
    SSH_PRIVATE_KEY = yamlConfig["ssh_private_key"]
    SSH_PUBLIC_KEY = yamlConfig["ssh_public_key"]
    SSH_KEYS_LOCAL_COPY_DIR = yamlConfig["ssh_keys_local_copy_dir"]
    SSH_KEYS_DIR = yamlConfig["ssh_keys_dir"]
    GIT_SSH_SCRIPT_NAME = yamlConfig["git_ssh_script_name"]
    GIT_SSH_SCRIPT_LOCAL_FOLDER = yamlConfig["git_ssh_script_local_folder"]

# Determines if a directory is under git control
def is_dir_under_git_control(dirName):
  """Determines if a directory on a server is under Git control.

  Args:
    dirName(str): directory name on the server for which we wish to determine
      whether it's under Git control

  Returns:
    bool: True if the directory on the server is under Git control, False
      otherwise.
  """
  gitRevParseCmd = "cd {} && git rev-parse --git-dir".format(dirName)
  with settings(hide("warnings", "stdout", "stderr"), warn_only=True):
    return run(gitRevParseCmd).succeeded

@task
def setup_server_for_git_clone(homeDir=None):
  """Fabric task that sets up the ssh keys and a wrapper script for GIT_SSH
  to allow cloning of private Github repositories.

  Args:
    homeDir(str, optional): home directory for the server. If not supplied or if
      `None` is supplied, the return value of the `fabric_helpers.get_home_dir`
      function is used
  """
  if homeDir is None:
    homeDir = fabric_helpers.get_home_dir()
  serverName = env.host
  serverPublicKeyPath = os.path.join(homeDir, SSH_KEYS_DIR, SSH_PUBLIC_KEY)
  serverPrivateKeyPath = os.path.join(homeDir, SSH_KEYS_DIR, SSH_PRIVATE_KEY)
  localPublicKey = os.path.join(SSH_KEYS_LOCAL_COPY_DIR, SSH_PUBLIC_KEY)
  localPrivateKey = os.path.join(SSH_KEYS_LOCAL_COPY_DIR, SSH_PRIVATE_KEY)
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
    upload_template(GIT_SSH_SCRIPT_NAME, gitSSHWrapperPath, use_jinja=True, 
      template_dir=GIT_SSH_SCRIPT_LOCAL_FOLDER, mode=0755,
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

def get_git_ssh_script_path(homeDir=None):
  """Returns the path to the git ssh script

  Args:
    homeDir(str, optional): home directory for the server. If not supplied or if
      `None` is supplied, the return value of the `fabric_helpers.get_home_dir`
      function is used

  Returns:
    str: the path to the git ssh script
  """
  if homeDir is None:
    homeDir = fabric_helpers.get_home_dir()
  return os.path.join(homeDir, GIT_SSH_SCRIPT_NAME)

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
  return os.path.join(homeDir, SSH_KEYS_DIR, SSH_PUBLIC_KEY)

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
  return os.path.join(homeDir, SSH_KEYS_DIR, SSH_PRIVATE_KEY)
