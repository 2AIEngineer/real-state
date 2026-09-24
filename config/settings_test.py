"""Settings of the test suite: the regular settings under the `test` profile.

The profile is chosen before `config.settings` reads the environment, so the
fast password hasher, the in-memory mailbox and the temporary media root apply
whatever the local `.env` says.
"""

import os

os.environ["ENVIRONMENT"] = "test"

from config.settings import *  # noqa: E402,F401,F403
