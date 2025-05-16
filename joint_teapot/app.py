import json
import os
import re
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, List

from filelock import FileLock
from git import Repo
from typer import Argument, Exit, Option, Typer, echo

from joint_teapot.config import Settings, set_settings, settings
from joint_teapot.teapot import Teapot
from joint_teapot.utils import joj3
from joint_teapot.utils.logger import logger, set_logger

if TYPE_CHECKING:
    pass

app = Typer(add_completion=False)


class Tea:
    _teapot = None

    @property
    def pot(self) -> Teapot:
        if not self._teapot:
            self._teapot = Teapot()
        return self._teapot


tea = Tea()  # lazy loader


@app.command("export-students", help="export students from canvas to csv file")
def export_students_to_csv(output_file: Path) -> None:
    tea.pot.canvas.export_students_to_csv(output_file)


@app.command(
    "invite-to-teams", help="invite all canvas students to gitea teams by team name"
)
def add_all_canvas_students_to_teams(team_names: List[str]) -> None:
    tea.pot.add_all_canvas_students_to_teams(team_names)


@app.command(
    "create-personal-repos",
    help="create personal repos on gitea for all canvas students",
)
def create_personal_repos_for_all_canvas_students(suffix: str = Option("")) -> None:
    tea.pot.create_personal_repos_for_all_canvas_students(suffix)


@app.command("create-teams", help="create teams on gitea by canvas groups")
def create_teams_and_repos_by_canvas_groups(group_prefix: str) -> None:
    tea.pot.create_teams_and_repos_by_canvas_groups(group_prefix)


@app.command("get-public-keys", help="list all public keys on gitea")
def get_public_key_of_all_canvas_students() -> None:
    res = []
    for k, v in tea.pot.get_public_key_of_all_canvas_students().items():
        keys = "\\n".join(v)
        res.append(f"{k},{keys}")
    echo("\n".join(res))


@app.command("clone-all-repos", help="clone all gitea repos to local")
def clone_all_repos() -> None:
    tea.pot.clone_all_repos()


@app.command("moss-all-repos", help="moss all gitea repos")
def moss_all_repos(language: str = "cc", wildcards: List[str] = ["*.*"]) -> None:
    url = tea.pot.moss_all_repos(language, wildcards)
    echo("Report Url: " + url)


@app.command("create-issues", help="create issues on gitea")
def create_issue_for_repos(
    repo_names: List[str],
    title: str,
    body: str = Argument(
        ..., help="issue body, or, if --from-file is set, filepath to issue body"
    ),
    from_file: bool = Option(False, "--file/--body"),
    use_regex: bool = Option(
        False, "--regex", help="repo_names takes list of regexes if set"
    ),
) -> None:
    tea.pot.create_issue_for_repos(repo_names, title, body, from_file, use_regex)


@app.command("create-comment", help="create a comment for an issue on gitea")
def create_comment(
    repo_name: str,
    index: int,
    body: str = Argument(..., help="comment body"),
) -> None:
    tea.pot.create_comment(repo_name, index, body)


@app.command("create-milestones", help="create milestones on gitea")
def create_milestone_for_repos(
    repo_names: List[str], title: str, description: str, due_on: datetime
) -> None:
    tea.pot.create_milestone_for_repos(repo_names, title, description, due_on)


@app.command("check-issues", help="check the existence of issue by title on gitea")
def check_exist_issue_by_title(repo_names: List[str], title: str) -> None:
    echo("\n".join(tea.pot.check_exist_issue_by_title(repo_names, title)))


@app.command(
    "checkout-releases",
    help="checkout git repo to git tag fetched from gitea by release name, with due date",
)
def checkout_to_repos_by_release_name(
    repo_names: List[str], release_name: str, due: datetime = Argument("3000-01-01")
) -> None:
    failed_repos = []
    succeed_repos = []
    for repo_name in repo_names:
        succeed = tea.pot.checkout_to_repo_by_release_name(repo_name, release_name, due)
        if not succeed:
            failed_repos.append(repo_name)
        else:
            succeed_repos.append(repo_name)
    echo(f"succeed repos: {succeed_repos}")
    echo(f"failed repos: {failed_repos}")


@app.command(
    "close-all-issues", help="close all issues and pull requests in gitea organization"
)
def close_all_issues() -> None:
    tea.pot.gitea.close_all_issues()


@app.command(
    "archive-repos", help="archive repos in gitea organization according to regex"
)
def archive_repos(regex: str = Argument(""), dry_run: bool = Option(True)) -> None:
    tea.pot.gitea.archive_repos(regex, dry_run)


@app.command("unwatch-all-repos", help="unwatch all repos in gitea organization")
def unwatch_all_repos() -> None:
    tea.pot.gitea.unwatch_all_repos()


@app.command("get-no-collaborator-repos", help="list all repos with no collaborators")
def get_no_collaborator_repos() -> None:
    tea.pot.gitea.get_no_collaborator_repos()


@app.command("get-repos-status", help="list status of all repos with conditions")
def get_repos_status(
    commit_lt: int = Argument(100000, help="commit count less than"),
    issue_lt: int = Argument(100000, help="issue count less than"),
) -> None:
    tea.pot.get_repos_status(commit_lt, issue_lt)


@app.command(
    "prepare-assignment-dir",
    help='prepare assignment dir from extracted canvas "Download Submissions" zip',
)
def prepare_assignment_dir(dir_or_zip_file: Path) -> None:
    tea.pot.canvas.prepare_assignment_dir(str(dir_or_zip_file))


@app.command(
    "upload-assignment-grades",
    help="upload assignment grades to canvas from grade file (GRADE.txt by default), "
    + "read the first line as grade, the rest as comments",
)
def upload_assignment_grades(assignments_dir: Path, assignment_name: str) -> None:
    tea.pot.canvas.upload_assignment_grades(str(assignments_dir), assignment_name)


@app.command(
    "create-group-channels-on-mm",
    help="create channels for student groups according to group information on"
    " gitea",
)
def create_group_channels_on_mm(
    prefix: str = Option(""),
    suffix: str = Option(""),
    invite_teaching_team: bool = Option(True),
) -> None:
    groups = {
        group_name: members
        for group_name, members in tea.pot.gitea.get_all_teams().items()
        if group_name.startswith(prefix)
    }
    logger.info(
        f"{len(groups)} channel(s) to be created"
        + (f" with suffix {suffix}" if suffix else "")
        + (", inviting teaching team" if invite_teaching_team else "")
        + f": {','.join(groups.keys())}"
    )
    tea.pot.mattermost.create_channels_for_groups(groups, suffix, invite_teaching_team)


@app.command(
    "create-personal-channels-on-mm",
    help="create channels for every student",
)
def create_personal_channels_on_mm(
    invite_teaching_team: bool = Option(True),
) -> None:
    tea.pot.create_channels_for_individuals(invite_teaching_team)


@app.command(
    "create-webhooks-for-mm",
    help="create a pair of webhooks on gitea and mm for all student groups on gitea, "
    "and configure them so that updates on gitea will be pushed to the mm channel",
)
def create_webhooks_for_mm(
    regex: str = Argument(""), git_suffix: bool = Option(False)
) -> None:
    repo_names = [
        group_name
        for group_name in tea.pot.gitea.get_all_teams()
        if re.match(regex, group_name)
    ]
    logger.info(f"{len(repo_names)} pair(s) of webhooks to be created: {repo_names}")
    tea.pot.mattermost.create_webhooks_for_repos(repo_names, tea.pot.gitea, git_suffix)


@app.command(
    "unsubscribe-from-repos",
    help="unsubscribe from all repos whose name match the given regex pattern",
)
def unsubscribe_from_repos(pattern: str = Argument("")) -> None:
    tea.pot.gitea.unsubscribe_from_repos(pattern)


@app.command(
    "joj3-all-env",
    help="run all joj3 tasks from env var and cli args",
)
def joj3_all_env(
    env_path: str = Argument("", help="path to .env file"),
    grading_repo_name: str = Option(
        "",
        help="name of grading repo to push failed table file",
    ),
    scoreboard_filename: str = Option(
        "scoreboard.csv", help="name of scoreboard file in the gitea repo"
    ),
    failed_table_filename: str = Option(
        "failed-table.md", help="name of failed table file in the gitea repo"
    ),
    max_total_score: int = Option(
        -1,
        help="max total score",
    ),
    skip_result_issue: bool = Option(
        False,
        help="skip creating result issue on gitea",
    ),
    skip_scoreboard: bool = Option(
        False,
        help="skip creating scoreboard on gitea",
    ),
    skip_failed_table: bool = Option(
        False,
        help="skip creating failed table on gitea",
    ),
    submitter_in_issue_title: bool = Option(
        True,
        help="whether to include submitter in issue title",
    ),
) -> None:
    app.pretty_exceptions_enable = False
    set_settings(Settings(_env_file=env_path))
    set_logger(settings.stderr_log_level)
    logger.info(f"debug log to file: {settings.log_file_path}")
    env = joj3.Env()
    if "" in (
        env.github_actor,
        env.github_run_number,
        env.github_sha,
        env.github_repository,
    ):
        logger.error("missing required env var")
        raise Exit(code=1)
    submitter_repo_name = env.github_repository.split("/")[-1]
    total_score = joj3.get_total_score(env.joj3_output_path)
    res = {
        "totalScore": total_score,
        "cappedTotalScore": (
            total_score if max_total_score < 0 else min(total_score, max_total_score)
        ),
        "forceQuit": env.joj3_force_quit_stage_name != "",
        "forceQuitStageName": env.joj3_force_quit_stage_name,
        "issue": 0,
        "action": int(env.github_run_number),
        "sha": env.github_sha,
        "commitMsg": env.joj3_commit_msg,
    }
    gitea_actions_url = (
        f"https://{settings.gitea_domain_name}{settings.gitea_suffix}/"
        + f"{settings.gitea_org_name}/{submitter_repo_name}/"
        + f"actions/runs/{env.github_run_number}"
    )
    submitter_repo_url = (
        f"https://{settings.gitea_domain_name}{settings.gitea_suffix}/"
        + f"{settings.gitea_org_name}/{submitter_repo_name}"
    )
    gitea_issue_url = ""
    if not skip_result_issue:
        issue_number = tea.pot.joj3_post_issue(
            env,
            max_total_score,
            gitea_actions_url,
            submitter_in_issue_title,
            submitter_repo_name,
        )
        res["issue"] = issue_number
    echo(json.dumps(res))  # print result to stdout for joj3 log parser
    if skip_scoreboard and skip_failed_table:
        return
    lock_file_path = os.path.join(
        settings.repos_dir, grading_repo_name, settings.joj3_lock_file_path
    )
    logger.info(
        f"try to acquire lock, file path: {lock_file_path}, "
        + f"timeout: {settings.joj3_lock_file_timeout}"
    )
    with FileLock(lock_file_path, timeout=settings.joj3_lock_file_timeout).acquire():
        logger.info("file lock acquired")
        retry_interval = 1
        git_push_ok = False
        while not git_push_ok:
            repo_path = tea.pot.git.repo_clean_and_checkout(
                grading_repo_name,
                "grading",
                clean_git_lock=True,
                reset_target="origin/grading",
            )
            repo: Repo = tea.pot.git.get_repo(grading_repo_name)
            if "grading" not in repo.remote().refs:
                logger.error(
                    '"grading" branch not found in remote, create and push it to origin first.'
                )
                raise Exit(code=1)
            if "grading" not in repo.branches:
                logger.error('"grading" branch not found in local, create it first.')
                raise Exit(code=1)
            repo.git.reset("--hard", "origin/grading")
            if not skip_scoreboard:
                joj3.generate_scoreboard(
                    env.joj3_output_path,
                    env.github_actor,
                    os.path.join(repo_path, scoreboard_filename),
                    env.joj3_conf_name,
                )
                tea.pot.git.add_commit(
                    grading_repo_name,
                    [scoreboard_filename],
                    (
                        f"joj3: update scoreboard for {env.joj3_conf_name} by @{env.github_actor} in "
                        f"{settings.gitea_org_name}/{submitter_repo_name}@{env.github_sha}\n\n"
                        f"gitea actions link: {gitea_actions_url}\n"
                        f"gitea issue link: {gitea_issue_url}\n"
                        f"groups: {env.joj3_groups}\n"
                    ),
                )
            if not skip_failed_table:
                joj3.generate_failed_table(
                    env.joj3_output_path,
                    submitter_repo_name,
                    submitter_repo_url,
                    os.path.join(repo_path, failed_table_filename),
                    gitea_actions_url,
                )
                tea.pot.git.add_commit(
                    grading_repo_name,
                    [failed_table_filename],
                    (
                        f"joj3: update failed table for {env.joj3_conf_name} by @{env.github_actor} in "
                        f"{settings.gitea_org_name}/{submitter_repo_name}@{env.github_sha}\n\n"
                        f"gitea actions link: {gitea_actions_url}\n"
                        f"gitea issue link: {gitea_issue_url}\n"
                        f"groups: {env.joj3_groups}\n"
                    ),
                )
            push_info_list = tea.pot.git.push(grading_repo_name)
            git_push_ok = push_info_list.error is None
            if not git_push_ok:
                retry_interval *= 2
                logger.info(
                    f"git push failed, retry in {retry_interval} seconds: {push_info_list}"
                )
                if retry_interval > 64:
                    logger.error(f"git push failed too many times")
                    raise Exit(code=1)
                sleep(retry_interval)
    logger.info("joj3-all-env done")


@app.command(
    "joj3-check-env",
    help="check joj3 restrictions from env var and cli args",
)
def joj3_check_env(
    env_path: str = Argument("", help="path to .env file"),
    grading_repo_name: str = Option(
        "grading",
        help="name of grading repo to push scoreboard file",
    ),
    scoreboard_filename: str = Option(
        "scoreboard.csv", help="name of scoreboard file in the gitea repo"
    ),
    group_config: str = Option(
        "=100:24",
        help=(
            "Configuration for groups in the format "
            "'group_name=max_count:time_period(in hours)'. "
            "Empty group name for all groups. "
            "Negative max_count or time_period for no limit. "
            "Example: --group-config joj=10:24,run=20:48"
        ),
    ),
) -> None:
    app.pretty_exceptions_enable = False
    set_settings(Settings(_env_file=env_path))
    set_logger(settings.stderr_log_level)
    logger.info(f"debug log to file: {settings.log_file_path}")
    env = joj3.Env()
    if "" in (
        env.github_actor,
        env.github_repository,
    ):
        logger.error("missing required env var")
        raise Exit(code=1)
    msg, failed = tea.pot.joj3_check_submission_count(
        env, grading_repo_name, group_config, scoreboard_filename
    )
    echo(json.dumps({"msg": msg, "failed": failed}))  # print result to stdout for joj3
    logger.info("joj3-check-env done")


if __name__ == "__main__":
    try:
        app()
    except Exception:
        logger.exception("Unexpected error:")
