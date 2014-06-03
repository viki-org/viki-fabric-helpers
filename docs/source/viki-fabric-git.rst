`viki.fabric.git` - A short guide
=================================

This page covers the use of the `viki.fabric.git` module. More detailed
documentation for individual functions in this module can be found in the
:ref:`API Documentation <api_viki_fabric_git>`.

Our focus here will be on running the `setup_server_for_git_clone` function.
This function is used to setup a server for Git remote operations (such as
cloning) involving secret repositories and assumes the following:

* Git remote operations are carried out using SSH
* An SSH private key is used for authentication to gain access to the secret
  repository

Configuration
-------------

For any code which imports the `viki.fabric.git` module, you will need to create
a `YAML <http://www.yaml.org/>`_ file with some keys:

**ssh_private_key**

  Basename of the SSH private key to copy to the server.

**ssh_public_key**

  Basename of the SSH public key to copy to the server.

**ssh_keys_local_copy_dir**

  Folder storing the `ssh_private_key` and `ssh_public_key` files on
  **your local machine**.

  The path to this folder can be relative to where the Python script that
  imports the `viki.fabric.git` module is run, or an absolute path.

**ssh_keys_dir**

  Folder on the remote server to copy the `ssh_private_key` and `ssh_public_key`
  files to.

  **NOTE:** This folder is **relative to the $HOME directory** of the
  **remote user** during Fabric execution. This should normally be set to the
  string `'.ssh'`.

**git_ssh_script_name**

  Basename of a template git wrapper script on **your local machine**.
  What this script should contain is outlined later in
  :ref:`this subsection <git_ssh_wrapper_contents>`.

  This file will be copied to the `$HOME` directory of the user on the remote
  server (for such a server and user involved in a Fabric task). You can set
  this to any valid filename. My personal preference for this value is the
  string `'gitwrap.sh'`.

**git_ssh_script_local_folder**

  Folder **on your local machine** containing the `git_ssh_script_name` file.

  The path to this folder can be relative to where the Python script that
  imports the `viki.fabric.git` module is run, or an absolute path.

Example YAML file (and what it implies)
---------------------------------------

.. code-block:: yaml

    ssh_private_key: "id_github_ssh_key"
    ssh_public_key: "id_github_ssh_key.pub"
    ssh_keys_local_copy_dir: "github-ssh-keys"
    ssh_keys_dir: ".ssh"
    git_ssh_script_name: "gitwrap.sh"
    git_ssh_script_local_folder: "templates"

Suppose that Fred, a user of our library, has a Python Fabric File located at
`/home/fred/freds-repo/fabfile.py`, which he runs from the
`/home/fred/freds-repo` folder. Based on the values in the YAML file:

* There should be a `/home/fred/freds-repo/github-ssh-keys` folder containing
  the `id_github_ssh_key` and `id_github_ssh_key.pub` SSH keypair.
* This SSH keypair will be copied to the `$HOME/.ssh` folder on the server
  during execution of the `setup_server_for_git_clone` Fabric task
* There is a `/home/fred/freds-repo/templates` folder containing the
  `gitwrap.sh` file. We shall take a look at what this file should contain in
  the next section.

.. _git_ssh_wrapper_contents:

Git SSH Wrapper file
--------------------

This is the file specified by the value of the `git_ssh_script_name` YAML key,
and should contain the following code:

.. code-block:: bash

    #!/bin/bash

    ssh -i {{ ssh_private_key_path }} $@

The `{{ ssh_private_key_path }}` part of the code will be replaced by the
`setup_server_for_git_clone` Fabric task before the script is copied to the
server (A temporary file or similar is used, so your file will not be
accidentally modified by this task).

Running the `setup_server_for_git_clone` Fabric task
----------------------------------------------------

Assume that our imaginary user Fred

* has everything setup as we mentioned above
* has his YAML file located at
  `/home/fred/freds-repo/config/viki_fabric_git.yaml`
* runs the `/home/fred/freds-repo/fabfile.py` file (contents right below) from
  the `/home/fred/freds-repo` folder, using this command:

.. code-block:: bash

    fab -H hostOne,hostTwo freds_fabric_task

Contents of `/home/fred/freds-repo/fabfile.py` Fabric script:

.. code-block:: python

    from fabric.api import env, task

    import os.path
    import viki.fabric.git as fabric_git

    # Fred uses SSH config
    env.use_ssh_config = True

    # NOTE: The `initialize` function for the `viki.fabric.git` module must
    #       be called once in the entire program, before the
    #       `setup_server_for_git_clone` task is run. The argument to this
    #       function is the path to the YAML file we described above.
    fabric_git.initialize(os.path.join("config", "viki_fabric_git.yaml"))

    @task
    def freds_fabric_task():
      # Fred wishes to setup the current server for handling secret repos
      fabric_git.setup_server_for_git_clone()
      # Fred's other code below

Suppose Fred's SSH config file looks like this (see the `env.use_ssh_config`
line in the code above to understand why we put this here)::

    Host hostOne
      Hostname 1.2.3.4
      User ubuntu

    Host hostTwo
      Hostname 1.2.3.5
      User ubuntu

The effect of successfully executing the `setup_server_for_git_clone` Fabric
task (it's part of the `freds_fabric_task`):

* For the `ubuntu` user on `hostOne` and `hostTwo`, the `$HOME/.ssh` folder
  should contain the `id_github_ssh_key` and `id_github_ssh_key.pub` SSH keypair
* A templated `$HOME/gitwrap.sh` should be present for the `ubuntu` user on
  those 2 servers

Now, the `ubuntu` user on Fred's `hostOne` and `hostTwo` servers are ready for
handling some secret git repositories. We shall go into that next.

Working with secret repos after running `setup_server_for_git_clone`
--------------------------------------------------------------------

Suppose Fred SSHes into `hostOne` using the `ubuntu` user, and wishes to clone a
secret repository whose clone url is `git@github.com:fred/top-secret-repo.git`,
he should use this bash command to clone the git repository:

.. code-block:: bash

    GIT_SSH=$HOME/gitwrap.sh git clone git@github.com:fred/top-secret-repo.git

In fact, this can be generalized to other Git remote operations for secret
repos, such as `git fetch`. The pattern for the command to use is:

.. code-block:: bash

    GIT_SSH=$HOME/gitwrap.sh <git command and args>

Which makes me wonder why we named the task `setup_server_for_git_clone`;
perhaps this was our original use case.
