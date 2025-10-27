import os
import logging
import logging.config

### THIS IS REQUIRED FOR GENEZIO SERVERLESS ENVIRONMENTS ###
# Detect if running in a read-only environment (serverless)
if os.access(os.getcwd(), os.W_OK):
    BASE_DIR = os.getcwd()  # local dev: project root
else:
    BASE_DIR = "/tmp"  # serverless-safe

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "app.log")


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "default": {
            "format": "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "DEBUG",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "level": "WARNING",
            "filename": log_file,
            "maxBytes": 1048576,  # 1MB
            "backupCount": 5,
        },
    },

    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG",
    },
}

# Suppress the python_multipart.multipart logger to WARNING instead of DEBUG
logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)

def setup_logging():
    """Setup logging using Python dict config."""
    
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logging.config.dictConfig(LOGGING_CONFIG)