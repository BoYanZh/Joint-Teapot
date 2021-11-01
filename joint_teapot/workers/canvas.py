import os
from glob import glob
from typing import cast

from canvasapi import Canvas as PyCanvas
from canvasapi.assignment import Assignment
from patoolib import extract_archive
from patoolib.util import PatoolError

from joint_teapot.config import settings
from joint_teapot.utils.logger import logger
from joint_teapot.utils.main import first, percentile


class Canvas:
    def __init__(
        self,
        access_token: str = settings.canvas_access_token,
        course_id: int = settings.canvas_course_id,
        grade_filename: str = "GRADE.txt",
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
        self.grade_filename = grade_filename
        logger.debug("Canvas initialized")

    def prepare_assignment_dir(
        self, dir_or_zip_file: str, create_grade_file: bool = True
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
            if create_grade_file:
                grade_file_path = os.path.join(new_path, self.grade_filename)
                if not os.path.exists(grade_file_path):
                    open(grade_file_path, mode="w")
        late_students = set()
        submitted_ids = set()
        for path in glob(os.path.join(dir, "*")):
            filename = os.path.basename(path)
            if "_" not in filename:
                continue
            segments = filename.split("_")
            if segments[1] == "late":
                file_id = int(segments[2])
            else:
                file_id = int(segments[1])
            login_id = login_ids[file_id]
            target_dir = os.path.join(dir, login_id)
            if segments[1] == "late":
                # TODO: check the delay time of late submission
                if create_grade_file:
                    grade_file_path = os.path.join(path, self.grade_filename)
                    if os.path.exists(grade_file_path):
                        open(grade_file_path, mode="a").write("LATE SUBMISSION\n")
                student = first(self.students, lambda x: x.login_id == login_id)
                late_students.add(student)
            try:
                extract_archive(path, outdir=target_dir, verbosity=-1)
                os.remove(path)
            except PatoolError:
                os.rename(path, os.path.join(target_dir, filename))
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

    def upload_assignment_grades(self, dir: str, assignment_name: str) -> None:
        assignment = first(self.assignments, lambda x: x.name == assignment_name)
        if assignment is None:
            logger.info(f"Canvas assignment {assignment_name} not found")
            return
        assignment = cast(Assignment, assignment)
        submission_dict = {}
        float_grades = []
        is_float_grades = True
        for submission in assignment.get_submissions():
            student = first(self.students, lambda x: x.id == submission.user_id)
            if student is None:
                continue
            grade_file_path = os.path.join(
                dir, student.sis_login_id, self.grade_filename
            )
            try:
                grade, *comments = list(open(grade_file_path))
                grade = grade.strip()
                try:
                    float_grades.append(float(grade))
                except ValueError:
                    is_float_grades = False
                data = {
                    "submission": {"posted_grade": grade},
                    "comment": {"text_comment": "".join(comments)},
                }
                submission_dict[(student, submission)] = data
                comment_no_newline = (
                    data["comment"]["text_comment"].strip().replace("\n", "  ")
                )
                logger.info(
                    f"Grade file parsed for {assignment} {student}: "
                    f"grade: {data['submission']['posted_grade']}, "
                    f'comment: "{comment_no_newline}"'
                )
            except Exception:
                logger.error(f"Can not parse grade file {grade_file_path}")
                return
        for (student, submission), data in submission_dict.items():
            logger.info(
                f"Uploading grade for {assignment} {student}: {data.__repr__()}"
            )
            submission.edit(**data)
        if is_float_grades and float_grades:
            summary = [
                min(float_grades),
                percentile(float_grades, 0.25),
                percentile(float_grades, 0.5),
                percentile(float_grades, 0.75),
                max(float_grades),
            ]
            average_grade = sum(float_grades) / len(float_grades)
            logger.info(
                f"Grades summary: "
                f"Min: {summary[0]:.2f}, "
                f"Q1: {summary[1]:.2f}, "
                f"Q2: {summary[2]:.2f}, "
                f"Q3: {summary[3]:.2f}, "
                f"Max: {summary[4]:.2f}, "
                f"Average: {average_grade:.2f}"
            )
        logger.info(f"Canvas assginemnt {assignment} grades upload succeed")


if __name__ == "__main__":
    canvas = Canvas()
