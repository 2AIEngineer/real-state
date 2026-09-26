"""Gunicorn settings. Resolved relative to the working directory (APP_PATH)."""

import multiprocessing
import os

# App Service routes traffic to WEBSITES_PORT (8000 by default).
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
# The instance also runs the outbox worker and the scheduler: keep headroom.
workers = int(min(multiprocessing.cpu_count() * 2 + 1, 5))
worker_class = "gthread"
threads = 2
# Below the 230 s App Service front-end timeout.
timeout = 220
graceful_timeout = 25
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
