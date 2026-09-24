"""Accounts: the account itself, its role, and where that role is exercised.

| Module | What it answers |
|---|---|
| `authorization` | The facts other modules build their policies on: who manages what, who works where, who lives there (`AccessService`). |
| `assignments` | Granting and revoking the places a role is exercised in, one service per table (a package). |
| `roles` | The single platform-wide role of an account (`RoleService`). |
| `accounts` | The account itself: creation, lookups, role, profile, e-mail (`AccountService`). |
| `status` | Deactivation, reactivation and closure with erasure of personal data (`AccountStatusService`). |
| `tokens` | Ending sessions: sign-out, revocation of every token (`TokenService`). |
| `setup_links` | The e-mailed link to choose a password, and its lifetime. |
| `registration` | What ties a new account to the residence: the units it owns or rents. |
| `passwords` | Choosing, resetting and changing passwords (`PasswordService`). |
| `providers` | The profile of service providers. |
| `technical` | Non-human accounts, such as a promoter's representative. |
| `session` | The `SessionContext` handed to the client after login (`SessionService`). |
| `directory` | Who holds a right in a property, to address notifications to them (`UserDirectory`). |
| `visibility` | The filter selecting the records addressed to a user's roles. |

Callers import the module they mean (`from apps.accounts.services.authorization
import AccessService`) rather than going through this file: `policies.py` reads
the facts of `authorization`, and `accounts.py` reads `policies`, so a package
re-exporting everything would close that loop into an import cycle.
"""
