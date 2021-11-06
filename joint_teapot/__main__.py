from joint_teapot.app import app
from joint_teapot.utils.logger import logger as logger

if __name__ == "__main__":
    try:
        app()
    except Exception:
        logger.exception("Unexpected error:")
