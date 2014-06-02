viki-fabric-helpers
===================

A library of [Fabric](http://www.fabfile.org/) helper functions used in some
of Viki's projects.

Example Usage:

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

A lot of work is needed to present more user-friendly documentation (especially
for the functions under the `viki.fabric.git` module), but every single function
has a docstring.
