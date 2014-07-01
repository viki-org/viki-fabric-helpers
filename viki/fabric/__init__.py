import os.path

import yaml

from fabric.api import env

__version__ = "0.0.2"

__VIKI_FABRIC_CONFIG_FILE_PATH__ = "viki_fabric_config.yml"

if os.path.exists(__VIKI_FABRIC_CONFIG_FILE_PATH__):
  with open(__VIKI_FABRIC_CONFIG_FILE_PATH__, "r") as f:
    env.viki_fabric_config = yaml.load(f.read())
