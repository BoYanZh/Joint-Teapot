import functools
import glob
import os
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, TypeVar

import mosspy
from git import Repo

from joint_teapot.config import settings
from joint_teapot.utils import joj3
from joint_teapot.utils.logger import logger
from joint_teapot.utils.main import default_repo_name_convertor, first
from joint_teapot.workers import Canvas, Git, Gitea, Mattermost
from joint_teapot.workers.joj import JOJ

if TYPE_CHECKING:
    import focs_gitea

_T = TypeVar("_T")


def for_all_methods(
    decorator: Callable[[Callable[[_T], _T]], Any],
) -> Callable[[_T], _T]:
    @functools.wraps(decorator)
    def decorate(cls: Any) -> Any:
        for attr in cls.__dict__:  # there's probably a better way to do this
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
    _mattermost = None

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

    @property
    def mattermost(self) -> Mattermost:
        if not self._mattermost:
            self._mattermost = Mattermost()
        return self._mattermost

    def __init__(self) -> None:
        logger.info(
            "Settings loaded. "
            f"Canvas Course ID: {settings.canvas_course_id}, "
            f"Gitea Organization name: {settings.gitea_org_name}, "
            f"Mattermost Team name: {settings.mattermost_team}@{settings.mattermost_domain_name}{settings.mattermost_suffix}"
        )
        logger.debug("Teapot initialized.")

    def add_all_canvas_students_to_teams(self, team_names: List[str]) -> None:
        return self.gitea.add_canvas_students_to_teams(self.canvas.students, team_names)

    def create_personal_repos_for_all_canvas_students(
        self, suffix: str = "", template: str = ""
    ) -> List[str]:
        return self.gitea.create_personal_repos_for_canvas_students(
            self.canvas.students,
            lambda user: default_repo_name_convertor(user) + suffix,
            template,
        )

    def create_teams_and_repos_by_canvas_groups(
        self, group_prefix: str = "", template: str = ""
    ) -> List[str]:
        def convertor(name: str) -> Optional[str]:
            if group_prefix and not name.startswith(group_prefix):
                return None
            team_name, number_str = name.split(" ")
            number = int(number_str)
            return f"{team_name}{number:02}"

        return self.gitea.create_teams_and_repos_by_canvas_groups(
            self.canvas.students, self.canvas.groups, convertor, convertor, template
        )

    def get_public_key_of_all_canvas_students(self) -> Dict[str, List[str]]:
        return self.gitea.get_public_key_of_canvas_students(self.canvas.students)

    def clone_all_repos(self) -> None:
        for i, repo_name in enumerate(self.gitea.get_all_repo_names()):
            logger.info(f"{i}, {self.gitea.org_name}/{repo_name} cloning...")
            self.git.repo_clean_and_checkout(repo_name, settings.default_branch)

    def moss_all_repos(self, language: str, wildcards: List[str]) -> str:
        m = mosspy.Moss(settings.moss_user_id, language)
        for repo_name in self.gitea.get_all_repo_names():
            base_dir = os.path.join(settings.repos_dir, repo_name)
            for wildcard in wildcards:
                full_wildcard = os.path.join(base_dir, wildcard)
                for file in glob.glob(full_wildcard, recursive=True):
                    if not os.path.isfile(file):
                        continue
                    logger.info(f"Adding file {file}")
                    m.files.append((file, os.path.relpath(file, settings.repos_dir)))
        logger.info("Sending files")
        return m.send()

    def create_issue_for_repos(
        self,
        repo_names: List[str],
        title: str,
        body: str,
        from_file: bool = False,
        use_regex: bool = False,
        milestone: str = "",
        labels: List[str] = [],
    ) -> None:
        if from_file:
            try:
                f = open(body)
                content = f.read()
                f.close()
            except FileNotFoundError:
                logger.error(f"file {body} not found")
                return
            except Exception as e:
                logger.exception("Error occurred when opening file {body}:")
                logger.error(e)
                return
        else:
            content = body

        affected_repos = []
        if use_regex:
            all_repos = self.gitea.get_all_repo_names()
            for pattern in repo_names:
                affected_repos.extend(
                    [repo for repo in all_repos if re.search(pattern, repo) is not None]
                )
        else:
            affected_repos = repo_names

        for repo_name in affected_repos:
            self.gitea.create_issue(repo_name, title, content, True, milestone, labels)

    def create_comment(
        self,
        repo_name: str,
        index: int,
        body: str,
    ) -> None:
        self.gitea.create_comment(repo_name, index, body)

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
        for repo_name, (
            commit_count,
            issue_count,
        ) in self.gitea.get_repos_status().items():
            if commit_count < commit_lt or issue_count < issue_lt:
                logger.info(
                    f"{self.gitea.org_name}/{repo_name} has "
                    f"{commit_count} commit(s), {issue_count} issue(s)"
                )

    def create_channels_for_individuals(
        self, invite_teaching_teams: bool = True
    ) -> None:
        return self.mattermost.create_channels_for_individuals(
            self.canvas.students, invite_teaching_teams
        )

    def joj3_post_issue(
        self,
        env: joj3.Env,
        max_total_score: int,
        gitea_actions_url: str,
        submitter_in_issue_title: bool,
        submitter_repo_name: str,
        issue_label_name: str,
        issue_label_color: str,
    ) -> int:
        title, comment = joj3.generate_title_and_comment(
            env.joj3_output_path,
            gitea_actions_url,
            env.github_run_number,
            env.joj3_conf_name,
            env.github_actor,
            env.github_sha,
            submitter_in_issue_title,
            env.joj3_run_id,
            max_total_score,
        )
        title_prefix = joj3.get_title_prefix(
            env.joj3_conf_name, env.github_actor, submitter_in_issue_title
        )
        joj3_issue: focs_gitea.Issue
        issue: focs_gitea.Issue
        new_issue = False
        for issue in self.gitea.issue_api.issue_list_issues(
            self.gitea.org_name, submitter_repo_name, state="open"
        ):
            if issue.title.startswith(title_prefix):
                joj3_issue = issue
                logger.info(f"found joj3 issue: #{joj3_issue.number}")
                break
        else:
            new_issue = True
            labels = self.gitea.issue_api.issue_list_labels(
                self.gitea.org_name, submitter_repo_name
            )
            label_id = 0
            for label in labels:
                if label.name == issue_label_name:
                    label_id = label.id
                    break
            else:
                label = self.gitea.issue_api.issue_create_label(
                    self.gitea.org_name,
                    submitter_repo_name,
                    body={"name": issue_label_name, "color": issue_label_color},
                )
                label_id = label.id
            joj3_issue = self.gitea.issue_api.issue_create_issue(
                self.gitea.org_name,
                submitter_repo_name,
                body={"title": title, "body": comment, "labels": [label_id]},
            )
            logger.info(f"created joj3 issue: #{joj3_issue.number}")
        gitea_issue_url = joj3_issue.html_url
        logger.info(f"gitea issue url: {gitea_issue_url}")
        if not new_issue:
            self.gitea.issue_api.issue_edit_issue(
                self.gitea.org_name,
                submitter_repo_name,
                joj3_issue.number,
                body={"title": title, "body": comment},
            )
        return joj3_issue.number

    def joj3_check_submission_time(
        self,
        begin_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Tuple[str, bool]:
        now = datetime.now()
        if (begin_time and now < begin_time) or (end_time and now > end_time):
            return (
                "### Submission Time Check Failed\n"
                f"Current time {now} is not in the valid range "
                f"[{begin_time}, {end_time}].\n",
                True,
            )
        return (
            "### Submission Time Check Passed\n"
            f"Current time {now} is in the valid range "
            f"[{begin_time}, {end_time}].\n",
            False,
        )

    def joj3_check_submission_count(
        self,
        env: joj3.Env,
        grading_repo_name: str,
        group_config: str,
        scoreboard_filename: str,
    ) -> Tuple[str, bool]:
        submitter_repo_name = env.github_repository.split("/")[-1]
        repo: Repo = self.git.get_repo(grading_repo_name)
        now = datetime.now(timezone.utc)
        items = group_config.split(",")
        comment = ""
        failed = False
        pattern = re.compile(
            r"joj3: update scoreboard for (?P<exercise_name>.+?) "
            r"by @(?P<submitter>.+) in "
            r"(?P<gitea_org_name>.+)/(?P<submitter_repo_name>.+)@(?P<commit_hash>.+)"
        )
        time_windows = []
        valid_items = []
        for item in items:
            name, values = item.split("=")
            max_count, time_period = map(int, values.split(":"))
            if max_count < 0 or time_period < 0:
                continue
            since = now - timedelta(hours=time_period)
            time_windows.append(since)
            valid_items.append((name, max_count, time_period, since))
        logger.info(f"valid items: {valid_items}, time windows: {time_windows}")
        all_commits = []
        if time_windows:
            earliest_since = min(time_windows).strftime("%Y-%m-%dT%H:%M:%S")
            commits = repo.iter_commits(paths=scoreboard_filename, since=earliest_since)
            for commit in commits:
                lines = commit.message.strip().splitlines()
                if not lines:
                    continue
                match = pattern.match(lines[0])
                if not match:
                    continue
                d = match.groupdict()
                if (
                    env.joj3_conf_name != d["exercise_name"]
                    or env.github_actor != d["submitter"]
                    or submitter_repo_name != d["submitter_repo_name"]
                ):
                    continue
                groups_line = next((l for l in lines if l.startswith("groups: ")), None)
                commit_groups = (
                    groups_line[len("groups: ") :].split(",") if groups_line else []
                )
                all_commits.append(
                    {
                        "time": commit.committed_datetime,
                        "groups": [g.strip() for g in commit_groups],
                    }
                )
        logger.info(f"all commits length: {len(all_commits)}")
        for name, max_count, time_period, since in valid_items:
            submit_count = 0
            time_limit = now - timedelta(hours=time_period)
            for commit in all_commits:
                if commit["time"] < time_limit:
                    continue
                if name:
                    target_group = name.lower()
                    commit_groups_lower = [g.lower() for g in commit["groups"]]
                    if target_group not in commit_groups_lower:
                        continue
                submit_count += 1
            logger.info(
                f"submitter {env.github_actor} is submitting for the {submit_count + 1} time, "
                f"{min(0, max_count - submit_count - 1)} time(s) remaining, "
                f"group={name}, "
                f"time period={time_period} hour(s), "
                f"max count={max_count}, submit count={submit_count}"
            )
            use_group = True
            if name:
                comment += f"keyword `{name}` "
                use_group = name.lower() in env.joj3_groups.lower()
            comment += (
                f"In last {time_period} hour(s): "
                f"submit count {submit_count}, "
                f"max count {max_count}"
            )
            if use_group and submit_count + 1 > max_count:
                failed = True
                comment += ", exceeded."
            else:
                comment += "."
            comment += "\n"
        if failed:
            title = "### Submission Count Check Failed"
        else:
            title = "### Submission Count Check Passed"
        msg = f"{title}\n{comment}\n"
        return msg, failed


if __name__ == "__main__":
    teapot = Teapot()
