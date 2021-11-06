__version__ = "0.0.0"

from joint_teapot.app import app
from joint_teapot.teapot import Teapot as Teapot
from joint_teapot.utils.logger import logger as logger


def main() -> None:
    app()
