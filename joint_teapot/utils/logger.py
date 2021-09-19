from sys import stderr

from loguru import logger as logger

from joint_teapot.config import settings

logger.remove()
logger.add(stderr, level="INFO")
logger.add(settings.log_file_path, level="INFO")
