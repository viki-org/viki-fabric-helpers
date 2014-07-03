Configuration
=============

This page describes how you can configure the viki-fabric-helpers library.

The `viki_fabric_config.yml` file
---------------------------------

The viki-fabric-helpers library makes use of a `viki_fabric_config.yml` file
for configuration. This file is read once, when any module under the
`viki.fabric` package is imported (the code is in the `viki/fabric/__init__.py`
file).

It is not necessary to provide the `viki_fabric_config.yml` file. If you do
provide it however, it should be located in the directory where the main Python
script is run.

Contents of the `viki_fabric_config.yml` file
---------------------------------------------

The `viki_fabric_config.yml` file is a `YAML <http://www.yaml.org/>`_ file.
If you are not familiar with YAML, it is a concise data representation format
for common data structures such as dictionaries and lists.
viki-fabric-helpers makes use of the `PyYAML <http://pyyaml.org/>`_ library for
reading YAML files.

Currently, only the `viki.fabric.git` module requires the
`viki_fabric_config.yml` file.
Refer to :doc:`viki-fabric-git` for more information.

**NOTE:** The `viki_fabric_config.yml` file can be used to hold other data
as long as their names do not conflict with those used by `viki-fabric-helpers`.

Accessing data in `viki_fabric_config.yml`
------------------------------------------

On your first import of a module under the `viki.fabric` package, the
`viki_fabric_config.yml` is read and its contents are placed inside the
`viki_fabric_config` key of the `fabric.api.env` variable. To access the data,
you should use the `viki.fabric.helpers.get_in_viki_fabric_config`.

For instance, suppose the `viki_fabric_config.yml` file has the following
contents:

.. code-block:: yaml

    animals:
      mammals:
        kangaroo: "jumps"
        human: "walks"
      reptiles:
        crocodle: "swims"
        lizard: "climbs"

To access the entire `animals` hash:

.. code-block:: python

    from viki.fabric.helpers import get_in_viki_fabric_config

    # obtain the dict {'mammals': ... , 'reptiles': ...}
    get_in_viki_fabric_config(["animals"])

To get the value of `animals.mammals.kangaroo`:

.. code-block:: python

    from viki.fabric.helpers import get_in_viki_fabric_config

    # obtains the string "jumps"
    get_in-viki_fabric_config(["animals", "mammals", "kangaroo"])
