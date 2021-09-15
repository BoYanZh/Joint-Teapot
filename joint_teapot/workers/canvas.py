from canvasapi import Canvas as PyCanvas
from loguru import logger

from joint_teapot.config import settings

# from canvasapi.group import Group, GroupMembership


class Canvas:
    def __init__(
        self,
        access_token: str = settings.canvas_access_token,
        course_id: int = settings.canvas_course_id,
    ):
        self.canvas = PyCanvas("https://umjicanvas.com/", access_token)
        self.course = self.canvas.get_course(course_id)
        logger.info(f"Canvas course loaded. {self.course}")
        self.students = self.course.get_users(
            enrollment_type=["student"], include=["email"]
        )
        for attr in ["sis_login_id", "sortable_name", "name"]:
            if not hasattr(self.students[0], attr):
                raise Exception(
                    f"Unable to gather students' {attr}, please contact the Canvas site admin"
                )
        logger.info(f"Canvas students loaded.")
        self.assignments = self.course.get_assignments()
        logger.info(f"Canvas assignments loaded.")
        self.groups = self.course.get_groups()
        logger.info(f"Canvas groups loaded.")
        logger.info("Canvas initialized.")


if __name__ == "__main__":
    canvas = Canvas()
