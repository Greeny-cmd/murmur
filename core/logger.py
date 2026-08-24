"""
Logger — simple logging setup.
"""

import logging
import os
from core import config

# Setup logging
log = logging.getLogger("murmur")
log.setLevel(logging.DEBUG)

# Console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
))
log.addHandler(console)

# File handler (optional — can be disabled in settings)
log_file = os.path.join(config.DATA_DIR, "murmur.log")
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
))


def set_file_log_enabled(enabled: bool) -> None:
    """Enable or disable writing logs to the log file."""
    if enabled:
        if file_handler not in log.handlers:
            log.addHandler(file_handler)
        file_handler.setLevel(logging.DEBUG)
        log.debug("File logging enabled: %s", log_file)
    else:
        if file_handler in log.handlers:
            log.removeHandler(file_handler)


set_file_log_enabled(getattr(config, "LOG_TO_FILE", True))
