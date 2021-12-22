import functools
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

from joint_teapot.config import settings
from joint_teapot.utils.logger import logger
from joint_teapot.utils.main import first
from joint_teapot.workers import Canvas, Git, Gitea
from joint_teapot.workers.joj import JOJ

_T = TypeVar("_T")


def for_all_methods(
    decorator: Callable[[Callable[[_T], _T]], Any]
) -> Callable[[_T], _T]:
    @functools.wraps(decorator)
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
    _joj = None

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

    @property
    def joj(self) -> JOJ:
        if not self._joj:
            self._joj = JOJ()
        return self._joj

    def __init__(self) -> None:
        logger.info(
            "Settings loaded. "
            f"Canvas Course ID: {settings.canvas_course_id}, "
            f"Gitea Organization name: {settings.gitea_org_name}"
        )
        logger.debug("Teapot initialized.")

    def add_all_canvas_students_to_teams(self, team_names: List[str]) -> None:
        return self.gitea.add_canvas_students_to_teams(self.canvas.students, team_names)

    def create_personal_repos_for_all_canvas_students(self) -> List[str]:
        return self.gitea.create_personal_repos_for_canvas_students(
            self.canvas.students
        )

    def create_teams_and_repos_by_canvas_groups(
        self, group_prefix: str = ""
    ) -> List[str]:
        def convertor(name: str) -> Optional[str]:
            if group_prefix and not name.startswith(group_prefix):
                return None
            team_name, number_str = name.split(" ")
            number = int(number_str)
            return f"{team_name}-{number:02}"

        return self.gitea.create_teams_and_repos_by_canvas_groups(
            self.canvas.students, self.canvas.groups, convertor, convertor
        )

    def get_public_key_of_all_canvas_students(self) -> Dict[str, List[str]]:
        return self.gitea.get_public_key_of_canvas_students(self.canvas.students)

    def clone_all_repos(self) -> None:
        for i, repo_name in enumerate(self.gitea.get_all_repo_names()):
            logger.info(f"{i}, {self.gitea.org_name}/{repo_name} cloning...")
            self.git.repo_clean_and_checkout(repo_name, "master")

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

    def checkout_to_repo_by_release_name(
        self, repo_name: str, release_name: str, due: datetime = datetime(3000, 1, 1)
    ) -> bool:
        repo_releases = self.gitea.get_repo_releases(repo_name)
        release = first(repo_releases, lambda item: item.name == release_name)
        if release is None or release.created_at.replace(tzinfo=None) >= due:
            logger.warning(
                f"{self.gitea.org_name}/{repo_name} checkout to "
                f"release by name {release_name} fail"
            )
            return False
        self.git.repo_clean_and_checkout(repo_name, f"tags/{release.tag_name}")
        logger.info(
            f"{self.gitea.org_name}/{repo_name} checkout to "
            f"tags/{release.tag_name} succeed"
        )
        return True

    def get_repos_status(self, commit_lt: int, issue_lt: int) -> None:
        for repo_name, commit_count, issue_count in self.gitea.get_repos_status():
            if commit_count < commit_lt or issue_count < issue_lt:
                logger.info(
                    f"{self.gitea.org_name}/{repo_name} has "
                    f"{commit_count} commit(s), {issue_count} issue(s)"
                )


if __name__ == "__main__":
    teapot = Teapot()
