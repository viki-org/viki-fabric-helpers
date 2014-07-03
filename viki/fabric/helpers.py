from fabric.api import env, run
from fabric.colors import blue, red, yellow
from fabric.context_managers import cd, hide, settings
from fabric.contrib.files import exists
from fabric.operations import get, put, sudo
from fabric.utils import abort

from viki.fabric import VIKI_FABRIC_CONFIG_KEY_NAME

import os
import os.path
import StringIO
import tempfile

def run_and_get_stdout(cmdString, hostString=None, useSudo=False):
  """Runs a command and grabs its output from standard output, without all the
  Fabric associated stuff and other crap (hopefully).

  Args:
    cmdString(str): Command to run

    hostString(str, optional): This should be passed the value of
      `env.host_string`

    useSudo(bool, optional): If `True`, `sudo` will be used instead of `run`
      to execute the command

  Returns:
    list of str: List of strings from running the command

  >>> run_and_get_stdout("ls")
  ["LICENSE", "README.md", "setup.py"]
  """
  return run_and_get_output(cmdString, hostString=hostString, useSudo=useSudo,
    captureStdout=True, captureStderr=False)["stdout"]

def run_and_get_output(cmdString, hostString=None, useSudo=False,
      captureStdout=True, captureStderr=True):
  """Runs a command and grabs its stdout and stderr, without all the Fabric
    associated stuff and other crap (hopefully).

  Args:
    cmdString(str): Command to run

    hostString(str, optional): This should be passed the value of
      `env.host_string`

    useSudo(bool, optional): If `True`, `sudo` will be used instead of `run`
      to execute the command

  Returns:
    dict: A Dict with 2 keys:
      "stdout": list(str) if captureStdout==True, `None` otherwise

      "stderr": list(str) if captureStderr==True, `None` otherwise

  >>> run_and_get_output("ls")
  { "stdout": ["LICENSE", "README.md", "setup.py"], "stderr": [] }
  """

  # takes a StringIO object
  def _remove_fabric_prefix(sio, prefix):
    prefixLen = len(prefix)
    linesList = sio.getvalue().split("\n")
    retList = []
    for (idx, line) in enumerate(linesList):
      if line == delimiterLine:
        retList = linesList[idx+1:]
        break
    for (idx, line) in enumerate(retList):
      if line.startswith(prefix):
        retList[idx] = line[prefixLen:]
    return retList

  if hostString is None:
    hostString = env.host_string
  devNull = open(os.devnull, "w")
  prefix = "[{}] out: ".format(hostString)
  delimiter = "START OF run_and_get_stdout delimiter"
  delimiterLine = "{}{}".format(prefix, delimiter)
  stdoutSIO = devNull
  stderrSIO = devNull
  if captureStdout:
    stdoutSIO = StringIO.StringIO()
  if captureStderr:
    stderrSIO = StringIO.StringIO()
  fabricRunOp = run
  if useSudo:
    fabricRunOp = sudo
  with settings(hide("running", "status"), warn_only=True):
    fabricRunOp("echo '{}' && {}".format(delimiter, cmdString),
      stdout=stdoutSIO, stderr=stderrSIO
    )
  devNull.close()
  retVal = { "stdout": None, "stderr": None }
  if captureStdout:
    retVal["stdout"] = _remove_fabric_prefix(stdoutSIO, prefix)
  if captureStderr:
    retVal["stderr"] = _remove_fabric_prefix(stderrSIO, prefix)
  return retVal

def get_home_dir():
  """Returns the home directory for the current user of a given server.

  Returns:
    str: the path to the home directory of the current host, or the string
      "$HOME"

  >>> get_home_dir()
  "/home/ubuntu"
  """
  outputList = run_and_get_stdout("echo $HOME")
  if outputList:
    return outputList[0].strip()
  else:
    return "$HOME"

# Downloads a remote file to a NamedTemporaryFile and invokes its .close()
# method.
# returns the name of the NamedTemporaryFile
def download_remote_file_to_tempfile(remoteFileName):
  """Downloads a file from a server to a \
  `tempfile.NamedTemporaryFile \
  <https://docs.python.org/2/library/tempfile.html#tempfile.NamedTemporaryFile>`_.

  **NOTE:** This function calls the `close` method on the NamedTemporaryFile.

  **NOTE:** The caller is reponsible for deleting the NamedTemporaryFile.

  Args:
    remoteFileName(str): name of the file on the server

  Returns:
    str: name of the temporary file whose contents is the same as the file on
      the server

  >>> downloadedFileName = download_remote_file_to_tempfile(
        "/home/ubuntu/a/search.rb"
      )
  >>> with open(downloadedFileName, "r") as f:
        # do some processing here...
  >>> os.unlink(downloadedFileName) # delete the file
  """
  downloadedDotfile = tempfile.NamedTemporaryFile(delete=False)
  downloadedDotfileName = downloadedDotfile.name
  downloadedDotfile.close()
  # hide warning of an existing file getting overwritten
  with settings(hide("warnings")):
    get(remoteFileName, downloadedDotfileName)
  return downloadedDotfileName

def copy_file_to_server_if_not_exists(localFileName, serverFileName):
  """Copies a file to the server if it does not exist there.

  Args:
    localFileName(str): local path of the file to copy to the server

    serverFileName(str): path on the server to copy to

  >>> copy_file_to_server_if_not_exists("helpers.py",
        os.path.join("my-repo", "helpers.py")
      )
  """
  serverName = env.host
  if not exists(serverFileName):
    print(yellow("`{}` does not exist on `{}`.".format(serverFileName,
      serverName
    )))
    print(yellow("Copying local `{}` to `{}` on `{}`...".format(
      localFileName, serverFileName, serverName
    )))
    put(localFileName, serverFileName, mirror_local_mode=True)
  else:
    print(blue("`{}` exists on `{}`".format(serverFileName, serverName)))

def is_dir(path):
  """Checks if a given path on the server is a directory.

  Args:
    path(str): path we wish to check

  Returns:
    bool: True if the given path on the server is a directory, False otherwise

  >>> is_dir("/home/ubuntu")
  True
  """
  with(settings(hide("everything"), warn_only=True)):
    return run("[ -d '{}' ]".format(path)).succeeded

def update_package_manager_package_lists():
  """Updates the package list of the package manager (currently assumed to be
  apt-get)

  >>> update_package_manage_package_lists()
  """
  sudo("apt-get update")

def install_software_using_package_manager(softwareList):
  """Installs a list of software using the system's package manager if they
  have not been installed. Currently this assumes `apt-get` to be the package
  manager.

  Args:
    softwareList(list of str): list of software to install

  >>> install_software_using_package_manager(
        ["vim", "openjdk-6-jdk", "unzip"]
      )
  """
  softwareToInstall = [software for software in softwareList if
    not is_installed_using_package_manager(software)]
  if softwareToInstall:
    print(yellow("Installing {} ...".format(",".join(softwareToInstall))))
    sudo("apt-get install -y {}".format(" ".join(softwareToInstall)))

def is_installed_using_package_manager(software):
  """Determines if a given software is installed on the system by its package
  manager (currently assumed to be apt-get).

  Args:
    software(str): The name of the software

  Return:
    bool: Returns True if the software is installed on the system using the
      package manager, False otherwise

  >>> is_installed_using_package_manager("python")
  True
  """
  outputList = run_and_get_stdout("dpkg -s {}".format(software))
  statusPrefix = "Status: "
  statusPrefixLen = len(statusPrefix)
  for line in outputList:
    if line.startswith(statusPrefix):
      return line[statusPrefixLen:].strip() == "install ok installed"
  return False

def setup_vundle(homeDir=None):
  """Clones the Vundle vim plugin (https://github.com/gmarik/Vundle.vim) to the
  server (if it hasn't been cloned), pulls updates, checkout v0.10.2, and
  installs vim plugins managed by Vundle.

  Args:
    homeDir(str, optional): home directory for the server. If not supplied or if
      `None` is supplied, the return value of the `get_home_dir` function is
      used

  >>> setup-vundle()
  """
  if homeDir is None:
    homeDir = get_home_dir()
  vundleGitRepoPath = os.path.join(homeDir, ".vim", "bundle", "Vundle.vim")
  if exists(vundleGitRepoPath):
    if not is_dir(vundleGitRepoPath):
      abort(red(
        ("Error: `{}` is not a directory. Please remove it manually (it is used"
         " for storing Vundle)."
        ).format(vundleGitRepoPath)
      ))
    # updates the repository
    with cd(vundleGitRepoPath):
      print(blue('Vundle git repo exists. Updating it...'))
      run('git remote update')
  else:
    print(yellow(
      'Vundle.vim not found. Cloning it to `{}`'.format(vundleGitRepoPath)
    ))
    gitCloneCmd = \
      'git clone https://github.com/gmarik/Vundle.vim.git {}'.format(
        vundleGitRepoPath
      )
    run(gitCloneCmd)

  with cd(vundleGitRepoPath):
    run('git checkout v0.10.2')
  print(yellow('Installing vim plugins managed by Vundle...'))
  with settings(hide('stdout')):
    run('vim +PluginInstall +qall')

def is_program_on_path(program):
  """Determines if a program is in any folder in the PATH environment variable.

  Args:
    program(str): Name of the program

  Return:
    bool: True if the program is in some folder in the PATH environment
      variable, False otherwise

  >>> is_program_on_path("python")
  True
  """
  with settings(hide("everything"), warn_only=True):
    return run("command -v {} >/dev/null 2>&1".format(program)).succeeded

def install_docker_most_recent():
  """Installs the most recent version of  docker (https://www.docker.io) using
  the http://get.docker.io shell script, and adds the current user to the
  docker group.

  **NOTE:** This function assumes that the bash shell exists, and that the
    user has sudo privileges.
  """
  run("wget -qO- https://get.docker.io/ | bash")
  sudo("usermod -aG docker {}".format(env.user))

def get_return_value_from_result_of_execute_runs_once(retVal):
  """Extracts one return value of a Fabric task decorated with
  `fabric.decorators.run_once` and ran with `fabric.tasks.execute`; this
  Fabric task should have the same return value for all hosts.

  Refer to the **Example Script** in :doc:`viki-fabric-docker` for an example
  of when to use this function.

  Args:
    retVal(dict): The return value of
      `fabric.tasks.execute(some_fabric_task, ...)`. `some_fabric_task`
      should be a Fabric task that only has local operations and is
      decorated with `fabric.decorators.runs_once`.
  """
  return retVal[retVal.keys()[0]]

def get_in_env(keyList, default=None):
  """Obtains the value under a series of nested keys in `fabric.api.env`; the
  value of every key in `keyList` 9except for the final key) is expected to be a
  dict.

  Args:
    keyList(list of str): list of keys under `fabric.api.env`

    default(obj, optional): The default value to return in case a key lookup
      fails

  >>> env
  {'liar': {'pants': {'on': 'fire'}, 'cuts': {'tree': 'leaf'}}, 'feed': {'ready': 'roll'}}
  >>> env_get_nested_keys(["liar"])
  {'pants': {'on': 'fire'}, 'cuts': {'tree': 'leaf'}}
  >>> env_get_nested_keys(["liar", "cuts"])
  {'tree': 'leaf'}
  >>> env_get_nested_keys(["feed", "ready"])
  'roll'
  >>> env_get_nested_keys(["feed", "ready", "roll"])
  None
  >>> env_get_nested_keys(["liar", "on"])
  None
  >>> env_get_nested_keys(["liar", "liar", "pants", "on", "fire"])
  None
  >>> env_get_nested_keys(["liar", "liar", "pants", "on", "fire"], "argh")
  'argh'
  """
  currentVal = env
  for k in keyList:
    if isinstance(currentVal, dict) and k in currentVal:
      currentVal = currentVal[k]
    else:
      return default
  return currentVal

def get_in_viki_fabric_config(keyList, default=None):
  """Calls `get_in_env`, but with the 0th element of the `keyList` set to
  `VIKI_FABRIC_CONFIG_KEY_NAME`.

  Args:
    keyList(list of str): list of keys under the `VIKI_FABRIC_CONFIG_KEY_NAME`
      key in `fabric.api.env`; **do not** include `VIKI_FABRIC_CONFIG_KEY_NAME`
      as the 0th element of this list

    default(obj, optional): The default value to return in case a key lookup
      fails

  >>> env
  {'viki_fabric_config': {'hierarchy': {'of': 'keys', 'king': {'pin': 'ship'}}}}}
  >>> get_in_viki_fabric_config(["hierarchy"])
  {"of": "keys", "king": {"pin": {"ship"}}}
  >>> get_in_viki_fabric_config(["hierarchy", "of"])
  'keys'
  >>> get_in_viki_fabric_config(["hierarchy", "of", "keys"])
  None
  >>> get_in_viki_fabric_config(["hierarchy", "notthere"])
  None
  >>> get_in_viki_fabric_config(["hierarchy", "pin"])
  None
  >>> get_in_viki_fabric_config(["hierarchy", "pin"], "useThis")
  'useThis'
  """
  return get_in_env([VIKI_FABRIC_CONFIG_KEY_NAME] + keyList,
    default=default
  )

def env_has_nested_keys(keyList):
  """Determines if `fabric.api.env` has a set of nested keys; the value of each
  key in `keyList` (except for the final key) is expected to be a dict

  Args:
    keyList(list of str): list of keys under `env`

  Returns:
    bool: True if `fabric.api.env` contains the series of nested keys, False
      otherwise

  >>> env
  {'whos': {'your': 'daddy', 'the': {'man': {'not': 'him'}}}}
  >>> env_has_nested_keys(['whos'])
  True
  >>> env_has_nested_keys(['your'])
  False
  >>> env_has_nested_keys(['whos', 'your'])
  True
  >>> env_has_nested_keys(['whos', 'your', 'daddy'])
  False
  >>> env_has_nested_keys(['whos', 'the', 'man'])
  True
  >>> env_has_nested_keys(['whos', 'man', 'not'])
  False
  """
  currentVal = env
  for k in keyList:
    if isinstance(currentVal, dict) and k in currentVal:
      currentVal = currentVal[k]
    else:
      return False
  return True
