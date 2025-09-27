# Gunicorn configuration file for Speech Processing App

import os
import multiprocessing

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)  # Cap at 8 workers
worker_class = "sync"
worker_connections = 1000
timeout = 300
keepalive = 2
max_requests = 1000
max_requests_jitter = 100

# Application
preload_app = True
chdir = "/var/www/speech-app"

# Logging
accesslog = "/var/log/speech-app/access.log"
errorlog = "/var/log/speech-app/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "speech-app"

# Server mechanics
daemon = False
pidfile = "/var/run/speech-app.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None

# SSL (uncomment if using SSL)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Environment
raw_env = [
    'FLASK_ENV=production',
]

# Worker tuning
worker_tmp_dir = "/dev/shm"  # Use shared memory for better performance

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190