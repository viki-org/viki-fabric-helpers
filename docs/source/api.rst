.. _api:

API Documentation
=================

viki.fabric.docker
------------------

.. module:: viki.fabric.docker

.. autofunction:: construct_tagged_docker_image_name

.. autofunction:: build_docker_image_from_git_repo

.. autofunction:: push_docker_image_to_registry

.. autofunction:: build_docker_image_from_git_repo_and_push_to_registry

.. autofunction:: pull_docker_image_from_registry


viki.fabric.helpers
-------------------

.. module:: viki.fabric.helpers

.. autofunction:: run_and_get_output

.. autofunction:: run_and_get_stdout

.. autofunction:: get_home_dir

.. autofunction:: download_remote_file_to_tempfile

.. autofunction:: copy_file_to_server_if_not_exists

.. autofunction:: is_dir

.. autofunction:: update_package_manager_package_lists

.. autofunction:: install_software_using_package_manager

.. autofunction:: is_installed_using_package_manager

.. autofunction:: setup_vundle

.. autofunction:: is_program_on_path

.. autofunction:: install_docker_most_recent

.. autofunction:: get_return_value_from_result_of_execute_runs_once

.. autofunction:: get_in_viki_fabric_config



.. _api_viki_fabric_git:

viki.fabric.git
---------------

.. module:: viki.fabric.git

.. autofunction:: is_dir_under_git_control

.. autofunction:: setup_server_for_git_clone

.. autofunction:: is_fabtask_setup_server_for_git_clone_run

.. autofunction:: get_git_ssh_script_path
