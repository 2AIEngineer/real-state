"""Settings of the test suite: the regular settings under the `test` profile.

The profile is chosen before `config.settings` reads the environment, so only
the database connection is taken from a local `.env` (see `config/env.py`):
local storage, UTC, default token lifetimes, fast password hasher, in-memory
mailbox and a temporary media root, whatever the `.env` says.
"""

import os

os.environ["ENVIRONMENT"] = "test"

from config.settings import *  # noqa: E402,F401,F403
