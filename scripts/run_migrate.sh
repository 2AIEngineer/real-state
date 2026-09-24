#!/bin/bash
uv run python manage.py migrate
uv run python manage.py create_default_superuser
uv run python manage.py create_platform_admin --email urbis@gmail.com
