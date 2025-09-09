import csv
import os
import re
from glob import glob
from pathlib import Path
from typing import cast

from canvasapi import Canvas as PyCanvas
from canvasapi.assignment import Assignment
from canvasapi.user import User
from patoolib import extract_archive
from patoolib.util import PatoolError

from joint_teapot.config import settings
from joint_teapot.utils.logger import logger
from joint_teapot.utils.main import first, percentile


class Canvas:
    def __init__(
        self,
        domain_name: str = "",
        suffix: str = "",
        access_token: str = "",  # nosec
        course_id: int = 0,
        grade_filename: str = "GRADE.txt",
    ):
        domain_name = domain_name or settings.canvas_domain_name
        suffix = suffix or settings.canvas_suffix
        access_token = access_token or settings.canvas_access_token
        course_id = course_id or settings.canvas_course_id
        self.canvas = PyCanvas(f"https://{domain_name}{suffix}", access_token)
        self.course = self.canvas.get_course(course_id)
        logger.info(f"Canvas course loaded. {self.course}")
        # types = ["student", "observer"]
        types = ["student"]

        def patch_user(student: User) -> User:
            student.name = (
                re.sub(r"[^\x00-\x7F]+", "", student.name).strip().title()
            )  # We only care english name
            student.sis_id = student.login_id
            student.login_id = student.email.split("@")[0]
            return student

        self.students = [
            patch_user(student)
            for student in self.course.get_users(enrollment_type=types)
        ]
        for attr in ["login_id", "name"]:
            if not hasattr(self.students[0], attr):
                raise Exception(
                    f"Unable to gather students' {attr}, please contact the Canvas site admin"
                )
        self.users = [patch_user(student) for student in self.course.get_users()]
        logger.debug("Canvas students loaded")
        self.assignments = self.course.get_assignments()
        logger.debug("Canvas assignments loaded")
        self.groups = self.course.get_groups()
        logger.debug("Canvas groups loaded")
        self.grade_filename = grade_filename
        logger.debug("Canvas initialized")

    def export_wrong_email_users(self) -> None:
        SAMPLE_EMAIL_BODY = """Dear Student,

We have noticed that you have changed your email address on Canvas. While this can clearly cause privacy issues, this also prevents you from joining Gitea which will be intensively used in this course. Please revert back to your SJTU email address (`jaccount@sjtu.edu.cn`) as soon as possible. Note that if your email address is still incorrect in 24 hours, we will have to apply penalties as this is slowing down the whole course progress.

Best regards,
Teaching Team"""
        emails = [
            user.email for user in self.users if not user.email.endswith("@sjtu.edu.cn")
        ]
        print(f"To: {','.join(emails)}")
        print(f"Subject: [{settings.gitea_org_name}] Important: wrong Canvas email")
        print(f"Body:\n{SAMPLE_EMAIL_BODY}")

    def export_users_to_csv(self, filename: Path) -> None:
        with open(filename, mode="w", newline="") as file:
            writer = csv.writer(file)
            for user in self.users:
                writer.writerow([user.name, user.sis_id, user.login_id])
        logger.info(f"Users exported to {filename}")

    def prepare_assignment_dir(
        self, dir_or_zip_file: str, create_grade_file: bool = True
    ) -> None:
        if os.path.isdir(dir_or_zip_file):
            assignments_dir = dir_or_zip_file
        else:
            assignments_dir = os.path.splitext(dir_or_zip_file)[0]
            if os.path.exists(assignments_dir):
                logger.error(
                    f"{assignments_dir} exists, can not unzip submissions file"
                )
                return
            extract_archive(dir_or_zip_file, outdir=assignments_dir, verbosity=-1)
        login_ids = {stu.id: stu.login_id for stu in self.students}
        for v in login_ids.values():
            new_path = os.path.join(assignments_dir, v)
            if not os.path.exists(new_path):
                os.mkdir(new_path)
            if create_grade_file:
                grade_file_path = os.path.join(new_path, self.grade_filename)
                if not os.path.exists(grade_file_path):
                    open(grade_file_path, mode="w")
        late_students = set()
        error_students = set()
        submitted_ids = set()
        for path in glob(os.path.join(assignments_dir, "*")):
            try:
                filename = os.path.basename(path)
                if "_" not in filename:
                    continue
                segments = filename.split("_")
                if segments[1] == "late":
                    file_id = int(segments[2])
                else:
                    file_id = int(segments[1])
                login_id = login_ids[file_id]
            except Exception:
                logger.error(f"Error on parsing path: {path}")
                continue
            student = first(self.students, lambda x: x.login_id == login_id)
            target_dir = os.path.join(assignments_dir, login_id)
            if segments[1] == "late":
                # TODO: check the delay time of late submission
                if create_grade_file:
                    grade_file_path = os.path.join(target_dir, self.grade_filename)
                    if os.path.exists(grade_file_path):
                        open(grade_file_path, mode="a").write("LATE SUBMISSION\n")
                late_students.add(student)
            try:
                extract_archive(path, outdir=target_dir, verbosity=-1)
                logger.info(f"Extract succeed: {student}")
                os.remove(path)
            except PatoolError as e:
                if not str(e).startswith("unknown archive format"):
                    logger.exception(f"Extract failed: {student}")
                    error_students.add(student)
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
        if error_students:
            tmp = ", ".join([str(student) for student in error_students])
            logger.info(f"Extract error student(s): {tmp}")

    def upload_assignment_grades(
        self, assignments_dir: str, assignment_name: str
    ) -> None:
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
                assignments_dir, student.login_id, self.grade_filename
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
