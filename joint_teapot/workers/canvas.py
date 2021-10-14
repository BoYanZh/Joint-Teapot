import os
from glob import glob

from canvasapi import Canvas as PyCanvas
from patoolib import extract_archive
from patoolib.util import PatoolError

from joint_teapot.config import settings
from joint_teapot.utils.logger import logger
from joint_teapot.utils.main import first


class Canvas:
    def __init__(
        self,
        access_token: str = settings.canvas_access_token,
        course_id: int = settings.canvas_course_id,
        score_filename: str = "SCORE.txt",
    ):
        self.canvas = PyCanvas("https://umjicanvas.com/", access_token)
        self.course = self.canvas.get_course(course_id)
        logger.info(f"Canvas course loaded. {self.course}")
        # types = ["student", "observer"]
        types = ["student"]
        self.students = self.course.get_users(enrollment_type=types, include=["email"])
        for attr in ["sis_login_id", "sortable_name", "name"]:
            if not hasattr(self.students[0], attr):
                raise Exception(
                    f"Unable to gather students' {attr}, please contact the Canvas site admin"
                )
        logger.debug(f"Canvas students loaded")
        self.assignments = self.course.get_assignments()
        logger.debug(f"Canvas assignments loaded")
        self.groups = self.course.get_groups()
        logger.debug(f"Canvas groups loaded")
        self.score_filename = score_filename
        logger.debug("Canvas initialized")

    def prepare_assignment_dir(
        self, dir_or_zip_file: str, create_score_file: bool = True
    ) -> None:
        if os.path.isdir(dir_or_zip_file):
            dir = dir_or_zip_file
        else:
            dir = os.path.splitext(dir_or_zip_file)[0]
            if os.path.exists(dir):
                logger.error(f"{dir} exists, can not unzip submissions file")
                return
            extract_archive(dir_or_zip_file, outdir=dir, verbosity=-1)
        login_ids = {stu.id: stu.login_id for stu in self.students}
        for v in login_ids.values():
            new_path = os.path.join(dir, v)
            if not os.path.exists(new_path):
                os.mkdir(new_path)
            if create_score_file:
                open(os.path.join(new_path, self.score_filename), mode="w")
        late_students = set()
        submitted_ids = set()
        for path in glob(os.path.join(dir, "*")):
            print(path)
            file_name = os.path.basename(path)
            if "_" not in file_name:
                continue
            segments = file_name.split("_")
            if segments[1] == "late":
                file_id = int(segments[2])
            else:
                file_id = int(segments[1])
            login_id = login_ids[file_id]
            if segments[1] == "late":
                student = first(self.students, lambda x: x.login_id == login_id)
                late_students.add(student)
            target_dir = os.path.join(dir, login_id)
            try:
                extract_archive(path, outdir=target_dir, verbosity=-1)
                os.remove(path)
            except PatoolError:
                os.rename(path, os.path.join(target_dir, file_name))
            submitted_ids.add(login_id)
        if login_ids:
            no_submission_students = [
                first(self.students, lambda x: x.login_id == login_id)
                for login_id in set(login_ids.values()) - submitted_ids
            ]
            if no_submission_students:
                tmp = ", ".join([str(student) for student in no_submission_students])
                logger.info(f"No submission student(s): {tmp}")
        if late_students:
            tmp = ", ".join([str(student) for student in late_students])
            logger.info(f"Late student(s): {tmp}")

    def upload_assignment_scores(self, dir: str, assignment_name: str) -> None:
        assignment = first(self.assignments, lambda x: x.name == assignment_name)
        if assignment is None:
            logger.info(f"Canvas assignment {assignment_name} not found")
            return
        for submission in assignment.get_submissions():
            student = first(self.students, lambda x: x.id == submission.user_id)
            if student is None:
                continue
            score_file_path = os.path.join(
                dir, student.sis_login_id, self.score_filename
            )
            score, *comments = list(open(score_file_path))
            data = {
                "submission": {"posted_grade": float(score)},
                "comment": {"text_comment": "".join(comments)},
            }
            logger.info(
                f"Uploading grade for {assignment} {student}: {data.__repr__()}"
            )
            submission.edit(**data)


if __name__ == "__main__":
    canvas = Canvas()
