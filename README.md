viki-fabric-helpers
===================

A library of [Fabric](http://www.fabfile.org/) helper functions used in some
of Viki's projects.

## Installation

To your `requirements.txt` file, add this line:

    viki-fabric-helpers

Or with the version pinned:

    viki-fabric-helpers==version-number

such as:

    viki-fabric-helpers==0.0.1

## Example Usage

```python
import os.path
from viki.fabric.helpers import get_home_dir, copy_file_to_server_if_not_exists

homeDir = get_home_dir()
# copy `users.db` locally to homeDir/users.db on the server, if that does
# not exist on the server
copy_file_to_server_if_not_exists('users.db',
  os.path.join(homeDir, 'users.db')
)
```

More functions are available in the `viki/fabric/helpers.py` and
`viki/fabric/git.py` files.

## Generating documentation

Execute this script:

    ./build_docs.sh

The docs will be generated at the `docs/build` folder.

## TODO

A lot of work is needed to present more user-friendly documentation (especially
for the functions under the `viki.fabric.git` module), but every single function
has a docstring.
