import multiprocessing
import os

# Configuración básica
bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"

# Timeouts aumentados para operaciones largas (como borrar organizaciones)
timeout = 120  # 2 minutos
graceful_timeout = 60
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
