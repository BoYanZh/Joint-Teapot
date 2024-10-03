import logging
import sys
from sys import stderr
from types import FrameType
from typing import Optional

from loguru import logger as logger

from joint_teapot.config import settings


# recipe from https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
class InterceptHandler(logging.Handler):
    def __init__(self, diagnose: bool = True, backtrace: bool = True):
        super().__init__()
        self.diagnose = diagnose
        self.backtrace = backtrace

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame: Optional[FrameType] = sys._getframe(6)
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage(), diagnose=self.diagnose, backtrace=self.backtrace
        )


def set_logger(
    stderr_log_level: str = settings.stderr_log_level,
    *,
    diagnose: bool = True,
    backtrace: bool = True,
) -> None:
    logging.basicConfig(
        handlers=[InterceptHandler(diagnose, backtrace)], level=0, force=True
    )
    logger.remove()
    logger.add(
        stderr,
        level=stderr_log_level,
        diagnose=diagnose,
        backtrace=backtrace,
    )
    logger.add(settings.log_file_path, level="DEBUG")


set_logger()
