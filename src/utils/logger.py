import logging
from logging.handlers import TimedRotatingFileHandler

from config.paths import LOGS_DIR

_LOGGER_CACHE = {}
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def get_logger(name: str = "handwrite") -> logging.Logger:
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(console)

        log_file = LOGS_DIR / "handwrite.log"
        file_handler = TimedRotatingFileHandler(
            log_file, when="midnight", backupCount=7, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(file_handler)

    _LOGGER_CACHE[name] = logger
    return logger
