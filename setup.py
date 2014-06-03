from setuptools import setup

import viki.fabric

setup(
  name="viki-fabric-helpers",
  version=viki.fabric.__version__,
  description="A library of Fabric helper functions",
  author="Viki Inc.",
  url="https://github.com/viki-org/viki-fabric-helpers",
  packages=["viki", "viki.fabric"],
  classifiers=[
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: BSD License",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: POSIX",
    "Operating System :: Unix",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Topic :: Software Development",
    "Topic :: Software Development :: Build Tools",
    "Topic :: Software Development :: Libraries",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: System :: Systems Administration",
  ],
  license="BSD",
  install_requires=["fabric", "jinja2", "PyYAML"],
)
