from typing import Any, Dict, List

from joint_teapot import Canvas, Git, Gitea


class Teapot:
    def __init__(self) -> None:
        self.canvas = Canvas()
        self.gitea = Gitea()
        self.git = Git()

    def create_personal_repos_for_all_canvas_students(self) -> List[str]:
        return self.gitea.create_personal_repos_for_canvas_students(
            self.canvas.students
        )

    def create_teams_and_repos_by_canvas_groups(self) -> List[str]:
        return self.gitea.create_teams_and_repos_by_canvas_groups(
            self.canvas.students, self.canvas.groups
        )

    def get_public_key_of_all_canvas_students(self) -> List[List[Dict[str, Any]]]:
        return self.gitea.get_public_key_of_canvas_students(self.canvas.students)

    def archieve_all_repos(self) -> List[str]:
        return [
            self.git.repo_clean_and_checkout(repo_name, "master")
            for repo_name in self.gitea.get_all_repo_names()
        ]

    def create_issue_for_repos(
        self, repo_names: List[str], title: str, body: str
    ) -> None:
        for repo_name in repo_names:
            self.gitea.create_issue(repo_name, title, body)


if __name__ == "__main__":
    teapot = Teapot()
