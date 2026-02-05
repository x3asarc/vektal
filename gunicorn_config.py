"""
Gunicorn WSGI server configuration
Used in production mode (Phase 13), not during development
"""
import multiprocessing

# Worker configuration
# Formula: (2 * CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Use sync workers (default)
# For I/O-bound async work, consider: worker_class = 'gevent'
worker_class = 'sync'

# Binding
bind = '0.0.0.0:5000'

# Timeout for long-running requests (AI analysis, scraping)
# Default 30s is too short for Vision AI calls
timeout = 120

# Logging to stdout/stderr for Docker
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Graceful restart timeout
graceful_timeout = 30

# Maximum requests per worker before restart (memory leak protection)
max_requests = 1000
max_requests_jitter = 50
