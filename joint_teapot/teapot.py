import functools
from datetime import datetime
from typing import Any, Callable, List

from joint_teapot.config import settings
from joint_teapot.utils.logger import logger
from joint_teapot.utils.main import first
from joint_teapot.workers import Canvas, Git, Gitea


def for_all_methods(decorator: Callable[..., Any]) -> Callable[..., Any]:
    def decorate(cls: Any) -> Any:
        for attr in cls.__dict__:  # there's propably a better way to do this
            if callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls

    return decorate


def log_exception_in_loguru(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def decorator(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(e)

    return decorator


@for_all_methods(log_exception_in_loguru)
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

    def __init__(self) -> None:
        logger.info(
            f"Settings loaded. Canvas Course ID: {settings.canvas_course_id}, Gitea Organization name: {settings.gitea_org_name}"
        )
        logger.debug("Teapot initialized.")

    def add_all_canvas_students_to_teams(self, team_names: List[str]) -> None:
        return self.gitea.add_canvas_students_to_teams(self.canvas.students, team_names)

    def create_personal_repos_for_all_canvas_students(self) -> List[str]:
        return self.gitea.create_personal_repos_for_canvas_students(
            self.canvas.students
        )

    def create_teams_and_repos_by_canvas_groups(self) -> List[str]:
        return self.gitea.create_teams_and_repos_by_canvas_groups(
            self.canvas.students, self.canvas.groups
        )

    def get_public_key_of_all_canvas_students(self) -> List[str]:
        return self.gitea.get_public_key_of_canvas_students(self.canvas.students)

    def clone_all_repos(self) -> List[str]:
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

    def close_all_issues(self) -> None:
        self.gitea.close_all_issues()

    def archieve_all_repos(self) -> None:
        self.gitea.archieve_all_repos()


if __name__ == "__main__":
    teapot = Teapot()
