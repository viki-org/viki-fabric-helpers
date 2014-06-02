from fabric.api import env, run
from fabric.colors import blue, red, yellow
from fabric.context_managers import cd, hide, settings
from fabric.contrib.files import exists
from fabric.operations import get, put, sudo
from fabric.utils import abort

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
    useSudo(bool, optional): If `True`, `sudo` will be used instead of `run` to
      execute the command

  Returns:
    list of str: List of strings from running the command
  """
  if hostString is None:
    hostString = env.host_string
  prefix = "[{}] out: ".format(hostString)
  prefixLen = len(prefix)
  delimiter = "START OF run_and_get_stdout delimiter"
  delimiterLine = "{}{}".format(prefix, delimiter)
  sio = StringIO.StringIO()
  fabricRunOp = run
  if useSudo:
    fabricRunOp = sudo
  with settings(hide("running", "status"), warn_only=True):
    fabricRunOp("echo '{}' && {}".format(delimiter, cmdString), stdout=sio)
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

def get_home_dir():
  """Returns the home directory for the current user of a given server.

  Returns:
    str: the path to the home directory of the current host, or the string
      "$HOME"
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
  """Downloads a file from a server to a tempfile.NamedTemporaryFile.

  NOTE: This function calls the `close` method on of the NamedTemporaryFile.
  NOTE: The caller is reponsible for deleting the NamedTemporaryFile.

  Args:
    remoteFileName(str): name of the file on the server

  Returns:
    str: name of the temporary file whose contents is the same as the file on
      the server
  """
  downloadedDotfile = tempfile.NamedTemporaryFile(delete=False)
  downloadedDotfileName = downloadedDotfile.name
  downloadedDotfile.close()
  # hide warning of an existing file getting overwritten
  with settings(hide("warnings")):
    get(remoteFileName, downloadedDotfileName)
  return downloadedDotfileName

def copy_file_to_server_if_not_exists(localFileName, serverFileName):
  """Copies a file to the server if it does not exist on the server.

  Args:
    localFileName(str): local path of the file to copy to the server
    serverFileName(str): path on the server to copy to
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
  """
  Checks if a given path is a directory

  Args:
    path(str): path we wish to check

  Returns:
    bool: True if the given path is a directory, False otherwise
  """
  with(settings(hide("everything"), warn_only=True)):
    return run("[ -d '{}' ]".format(path)).succeeded

def update_package_manager_package_lists():
  """Updates the package list of the package manager (currently assumed to be
  apt-get)
  """
  sudo("apt-get update")

def install_software_using_package_manager(softwareList):
  """Installs a list of software using the system's package manager if they
  have not been installed. Currently this assumes `apt-get` to be the package
  manager.

  Args:
    softwareList(list of str): list of software to install
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
