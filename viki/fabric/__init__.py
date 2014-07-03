import os.path

import yaml

from fabric.api import env

__version__ = "0.0.2"

__VIKI_FABRIC_CONFIG_FILE_PATH__ = "viki_fabric_config.yml"

# The key in the `env` dict that holds configuration settings read from the
# the `__VIKI_FABRIC_CONFIG_FILE_PATH__` YAML file
VIKI_FABRIC_CONFIG_KEY_NAME = "viki_fabric_config"

if os.path.exists(__VIKI_FABRIC_CONFIG_FILE_PATH__):
  with open(__VIKI_FABRIC_CONFIG_FILE_PATH__, "r") as f:
    env[VIKI_FABRIC_CONFIG_KEY_NAME] = yaml.load(f.read())
