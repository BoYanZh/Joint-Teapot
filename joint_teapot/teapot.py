from datetime import datetime
from typing import Any, Dict, List

from joint_teapot.utils import first
from joint_teapot.workers import Canvas, Git, Gitea


class Teapot:
    _canvas = None
    _gitea = None
    _git = None

    @property
    def canvas(self) -> Canvas:
        if not self._canvas:
            self._canvas = Canvas()
        return self._canvas

    @property
    def gitea(self) -> Gitea:
        if not self._gitea:
            self._gitea = Gitea()
        return self._gitea

    @property
    def git(self) -> Git:
        if not self._git:
            self._git = Git()
        return self._git

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

    def check_exist_issue_by_title(
        self, repo_names: List[str], title: str
    ) -> List[str]:
        res = []
        for repo_name in repo_names:
            if not self.gitea.check_exist_issue_by_title(repo_name, title):
                res.append(repo_name)
        return res

    def checkout_to_repos_by_release_name(
        self,
        repo_names: List[str],
        release_name: str,
        due: datetime = datetime(3000, 1, 1),
    ) -> List[str]:
        failed_repos = []
        repos_releases = self.gitea.get_repos_releases(repo_names)
        for repo_name, repo_releases in zip(repo_names, repos_releases):
            release = first(repo_releases, lambda item: item["name"] == release_name)
            if (
                release is None
                or datetime.strptime(release["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
                >= due
            ):
                failed_repos.append(repo_name)
                continue
            self.git.repo_clean_and_checkout(repo_name, f"tags/{release['tag_name']}")
        return failed_repos


if __name__ == "__main__":
    teapot = Teapot()
