import glob
import json
import ntpath
import os
from typing import cast

from canvasapi.assignment import Assignment

from joint_teapot import Teapot, logger
from joint_teapot.utils.main import default_repo_name_convertor, first, percentile


class VE482Teapot(Teapot):
    def p1_check(self) -> None:
        fault_repos = []
        for repo_name in self.gitea.get_all_repo_names():
            if not repo_name.endswith("p1"):
                continue
            faults = []
            succeed = self.checkout_to_repo_by_release_name(repo_name, "p1")
            if succeed:
                contain_c_file = False
                contain_readme_file = False
                for fn in glob.glob(f"{self.git.repos_dir}/{repo_name}/*"):
                    basename = ntpath.basename(fn)
                    if basename.endswith(".c"):
                        contain_c_file = True
                    if basename.lower().startswith("readme"):
                        contain_readme_file = True
                if not contain_c_file:
                    faults.append(
                        "no C file found in root directory in release p1, "
                        "can not compile on JOJ"
                    )
                if not contain_readme_file:
                    faults.append(
                        "no README file found in root directory in release p1"
                    )
            else:
                faults.append("no release named p1")
            if faults:
                fault_string = ""
                for fault in faults:
                    fault_string += f"- {fault}\n"
                logger.info("\n".join(("", repo_name, "", fault_string)))
                self.gitea.issue_api.issue_create_issue(
                    self.gitea.org_name,
                    repo_name,
                    body={
                        "body": fault_string,
                        "title": "p1 submission pre-check failed",
                    },
                )
                fault_repos.append(repo_name)
        logger.info(f"{len(fault_repos)} fault repo(s): {fault_repos}")

    def p1_submit(self) -> None:
        res_dict = {}
        assignment_name = "p1.3"
        assignment = first(self.canvas.assignments, lambda x: x.name == assignment_name)
        if assignment is None:
            logger.info(f"Canvas assignment {assignment_name} not found")
            return
        assignment = cast(Assignment, assignment)
        students = self.canvas.students
        for submission in assignment.get_submissions():
            student = first(students, lambda x: x.id == submission.user_id)
            if student is None:
                continue
            repo_name = default_repo_name_convertor(student) + "-p1"
            repo_dir = os.path.join(self.git.repos_dir, repo_name)
            base_score, base_url = self.joj.submit_dir(
                "https://joj.sjtu.edu.cn/d/ve482_fall_2021/p/61c2d0b27fe7290006b27034",
                repo_dir,
                "make",
            )
            bonus_score, bonus_url = self.joj.submit_dir(
                "https://joj.sjtu.edu.cn/d/ve482_fall_2021/p/61c2d49e7fe7290006b2703e",
                repo_dir,
                "make",
            )
            total_score = base_score / 520 * 100 + bonus_score / 220 * 30
            res_dict[student.sis_login_id] = total_score
            data = {
                "submission": {"posted_grade": round(total_score, 2)},
                "comment": {
                    "text_comment": (
                        f"base score: {base_score} / 520, url: {base_url}\n"
                        f"bonus score: {bonus_score} / 220, url: {bonus_url}\n"
                        f"total score: {base_score} / 520 * 100 + "
                        f"{bonus_score} / 220 * 30"
                    )
                },
            }
            submission.edit(**data)
        float_grades = list(res_dict.values())
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
        json.dump(
            res_dict, open("ve482_p1_grade.json", "w"), ensure_ascii=False, indent=4
        )


if __name__ == "__main__":
    teapot = VE482Teapot()
    teapot.p1_submit()
