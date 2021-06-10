from canvasapi import Canvas as PyCanvas

from joint_teapot.config import settings

# from canvasapi.group import Group, GroupMembership


class Canvas:
    def __init__(
        self,
        access_token: str = settings.canvas_access_token,
        courseID: int = settings.course_id,
    ):
        self.canvas = PyCanvas("https://umjicanvas.com/", access_token)
        self.course = self.canvas.get_course(courseID)
        self.students = self.course.get_users(
            enrollment_type=["student"], include=["email"]
        )
        self.assignments = self.course.get_assignments()
        self.groups = self.course.get_groups()
        for attr in ["sis_login_id", "sortable_name"]:
            if not hasattr(self.students[0], attr):
                raise Exception(
                    f"Unable to gather students' {attr}, please contact the Canvas site admin"
                )
        # group: Group
        # for group in self.groups:
        #     membership: GroupMembership
        #     print(group.__dict__)
        #     for membership in group.get_memberships():
        #         print(membership.user_id, end=", ")
        #     print("")


if __name__ == "__main__":
    canvas = Canvas()
