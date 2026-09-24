#!/bin/bash
# Azure App Service entry point: prepare the database, then hand over to supervisord.
set -euo pipefail

cd "$APP_PATH"
source antenv/bin/activate

python3 manage.py migrate --noinput
python3 manage.py create_default_superuser

exec supervisord -c "$APP_PATH/supervisord.conf"
