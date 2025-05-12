import multiprocessing
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 2  # Reduced from 4 to 2 for better stability
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120  # Increased timeout
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "debug"

# Process naming
proc_name = "phone-chatbot"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL
keyfile = None
certfile = None
ssl_version = 2
cert_reqs = 0
ca_certs = None
suppress_ragged_eofs = True

# Server hooks
def on_starting(server):
    """Log when the server is starting."""
    server.log.info("Starting phone-chatbot server")

def on_reload(server):
    """Log when the server is reloading."""
    server.log.info("Reloading phone-chatbot server")

def when_ready(server):
    """Log when the server is ready to accept connections."""
    server.log.info("Phone-chatbot server is ready")

def post_fork(server, worker):
    """Log after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_fork(server, worker):
    """Log before a worker is forked."""
    pass

def pre_exec(server):
    """Log before a new master process is forked."""
    server.log.info("Forked master process")

def worker_int(worker):
    """Log when a worker receives SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def worker_abort(worker):
    """Log when a worker receives SIGABRT."""
    worker.log.info("Worker received ABORT signal")

def worker_exit(server, worker):
    """Log when a worker exits."""
    server.log.info(f"Worker exited (pid: {worker.pid})")

def nworkers_changed(server, new_value, old_value):
    """Log when the number of workers changes."""
    server.log.info(f"Number of workers changed from {old_value} to {new_value}")

def on_exit(server):
    """Log when the server exits."""
    server.log.info("Phone-chatbot server is shutting down") 