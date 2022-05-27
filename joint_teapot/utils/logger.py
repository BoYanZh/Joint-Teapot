from sys import stderr

from loguru import logger as logger

from joint_teapot.config import settings


def set_logger(stderr_log_level: str = settings.stderr_log_level) -> None:
    logger.remove()
    logger.add(stderr, level=stderr_log_level)
    logger.add(settings.log_file_path, level="DEBUG")


set_logger()
