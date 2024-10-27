import os
from datetime import datetime
from pathlib import Path
from typing import List

from filelock import FileLock
from git import Repo
from typer import Argument, Option, Typer, echo

from joint_teapot.config import Settings, set_settings, settings
from joint_teapot.teapot import Teapot
from joint_teapot.utils import joj3
from joint_teapot.utils.logger import logger, set_logger

app = Typer(add_completion=False)


class Tea:
    _teapot = None

    @property
    def pot(self) -> Teapot:
        if not self._teapot:
            self._teapot = Teapot()
        return self._teapot


tea = Tea()  # lazy loader


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


@app.command("archive-all-repos", help="archive all repos in gitea organization")
def archive_all_repos() -> None:
    tea.pot.gitea.archive_all_repos()


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
    "create-channels-on-mm",
    help="create channels for student groups according to group information on"
    " gitea",
)
def create_channels_on_mm(
    prefix: str = Option(""),
    suffix: str = Option(""),
    invite_teaching_team: bool = Option(False),
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
    "create-webhooks-for-mm",
    help="create a pair of webhooks on gitea and mm for all student groups on gitea, "
    "and configure them so that updates on gitea will be pushed to the mm channel",
)
def create_webhooks_for_mm(prefix: str = Argument("")) -> None:
    repo_names = [
        group_name
        for group_name in tea.pot.gitea.get_all_teams()
        if group_name.startswith(prefix)
    ]
    logger.info(f"{len(repo_names)} pair(s) of webhooks to be created: {repo_names}")
    tea.pot.mattermost.create_webhooks_for_repos(repo_names, tea.pot.gitea)


@app.command(
    "unsubscribe-from-repos",
    help="unsubscribe from all repos whose name match the given regex pattern",
)
def unsubscribe_from_repos(pattern: str = Argument("")) -> None:
    tea.pot.gitea.unsubscribe_from_repos(pattern)


@app.command(
    "joj3-scoreboard",
    help="parse JOJ3 score json file into scoreboard and upload to gitea",
)
def joj3_scoreboard(
    env_path: str = Argument("", help="path to .env file"),
    score_file_path: str = Argument(
        "", help="path to score json file generated by JOJ3"
    ),
    submitter: str = Argument("", help="submitter ID"),
    repo_name: str = Argument(
        "",
        help="name of grading repo to push scoreboard file",
    ),
    submitter_repo_name: str = Argument(
        "",
        help="repository's name of the submitter",
    ),
    run_number: str = Argument(
        "",
        help="gitea actions run number",
    ),
    scoreboard_file_name: str = Argument(
        "scoreboard.csv", help="name of scoreboard file in the gitea repo"
    ),
    exercise_name: str = Argument(
        "unknown",
        help="name of the exercise that appears on the issue title",
    ),
    commit_hash: str = Argument(
        "",
        help="commit hash that triggers gitea actions",
    ),
) -> None:
    set_settings(Settings(_env_file=env_path))
    set_logger(settings.stderr_log_level, diagnose=False, backtrace=False)
    logger.info(f"debug log to file: {settings.log_file_path}")
    if joj3.check_skipped(score_file_path, "skip-scoreboard"):
        return
    tea.pot.git  # trigger lazy load
    lock_file_path = os.path.join(
        settings.repos_dir, repo_name, settings.joj3_lock_file_path
    )
    logger.info(
        f"try to acquire lock, file path: {lock_file_path}, "
        + f"timeout: {settings.joj3_lock_file_timeout}"
    )
    with FileLock(lock_file_path, timeout=settings.joj3_lock_file_timeout).acquire():
        logger.info("file lock acquired")
        repo_path = tea.pot.git.repo_clean_and_checkout(repo_name, "grading")
        repo: Repo = tea.pot.git.get_repo(repo_name)
        if "grading" not in repo.remote().refs:
            logger.error(
                '"grading" branch not found in remote, create and push it to origin first.'
            )
            return
        if "grading" not in repo.branches:
            logger.error('"grading" branch not found in local, create it first.')
            return
        repo.git.reset("--hard", "origin/grading")
        joj3.generate_scoreboard(
            score_file_path,
            submitter,
            os.path.join(repo_path, scoreboard_file_name),
            exercise_name,
        )
        actions_link = (
            f"https://{settings.gitea_domain_name}{settings.gitea_suffix}/"
            + f"{settings.gitea_org_name}/{submitter_repo_name}/"
            + f"actions/runs/{run_number}"
        )
        commit_message = (
            f"joj3: update scoreboard by @{submitter} in "
            + f"{settings.gitea_org_name}/{submitter_repo_name}@{commit_hash}\n\n"
            + f"gitea actions link: {actions_link}"
        )
        tea.pot.git.add_commit(repo_name, [scoreboard_file_name], commit_message)
        tea.pot.git.push(repo_name)


@app.command(
    "joj3-failed-table",
    help="parse JOJ3 score json file into failed table markdown file and upload to gitea",
)
def joj3_failed_table(
    env_path: str = Argument("", help="path to .env file"),
    score_file_path: str = Argument(
        "", help="path to score json file generated by JOJ3"
    ),
    submitter: str = Argument("", help="submitter ID"),
    repo_name: str = Argument(
        "",
        help="name of grading repo to push failed table file",
    ),
    submitter_repo_name: str = Argument(
        "",
        help="repository's name of the submitter",
    ),
    run_number: str = Argument(
        "",
        help="gitea actions run number",
    ),
    failed_table_file_name: str = Argument(
        "failed-table.md", help="name of failed table file in the gitea repo"
    ),
    exercise_name: str = Argument(
        "unknown",
        help="name of the exercise that appears on the issue title",
    ),
    commit_hash: str = Argument(
        "",
        help="commit hash that triggers gitea actions",
    ),
) -> None:
    set_settings(Settings(_env_file=env_path))
    set_logger(settings.stderr_log_level, diagnose=False, backtrace=False)
    logger.info(f"debug log to file: {settings.log_file_path}")
    if joj3.check_skipped(score_file_path, "skip-failed-table"):
        return
    tea.pot.git  # trigger lazy load
    lock_file_path = os.path.join(
        settings.repos_dir, repo_name, settings.joj3_lock_file_path
    )
    logger.info(
        f"try to acquire lock, file path: {lock_file_path}, "
        + f"timeout: {settings.joj3_lock_file_timeout}"
    )
    with FileLock(lock_file_path, timeout=settings.joj3_lock_file_timeout).acquire():
        logger.info("file lock acquired")
        repo_path = tea.pot.git.repo_clean_and_checkout(repo_name, "grading")
        repo: Repo = tea.pot.git.get_repo(repo_name)
        if "grading" not in repo.remote().refs:
            logger.error(
                '"grading" branch not found in remote, create and push it to origin first.'
            )
            return
        if "grading" not in repo.branches:
            logger.error('"grading" branch not found in local, create it first.')
            return
        repo.git.reset("--hard", "origin/grading")
        submitter_repo_link = (
            f"https://{settings.gitea_domain_name}{settings.gitea_suffix}/"
            + f"{settings.gitea_org_name}/{submitter_repo_name}"
        )
        actions_link = (
            f"https://{settings.gitea_domain_name}{settings.gitea_suffix}/"
            + f"{settings.gitea_org_name}/{submitter_repo_name}/"
            + f"actions/runs/{run_number}"
        )
        joj3.generate_failed_table(
            score_file_path,
            submitter_repo_name,
            submitter_repo_link,
            os.path.join(repo_path, failed_table_file_name),
            actions_link,
        )
        commit_message = (
            f"joj3: update failed table by @{submitter} in "
            + f"{settings.gitea_org_name}/{submitter_repo_name}@{commit_hash}\n\n"
            + f"gitea actions link: {actions_link}"
        )
        tea.pot.git.add_commit(repo_name, [failed_table_file_name], commit_message)
        tea.pot.git.push(repo_name)


@app.command(
    "joj3-create-result-issue",
    help="create result issue on gitea",
)
def joj3_create_result_issue(
    env_path: str = Argument("", help="path to .env file"),
    score_file_path: str = Argument(
        "", help="path to score json file generated by JOJ3"
    ),
    submitter_repo_name: str = Argument(
        "",
        help="repository's name of the submitter",
    ),
    run_number: str = Argument(
        "",
        help="gitea actions run number",
    ),
    exercise_name: str = Argument(
        "unknown",
        help="name of the exercise that appears on the issue title",
    ),
    submitter: str = Argument("", help="submitter ID"),
    commit_hash: str = Argument(
        "",
        help="commit hash that triggers gitea actions",
    ),
) -> None:
    set_settings(Settings(_env_file=env_path))
    set_logger(settings.stderr_log_level, diagnose=False, backtrace=False)
    logger.info(f"debug log to file: {settings.log_file_path}")
    if joj3.check_skipped(score_file_path, "skip-result-issue"):
        return
    actions_link = (
        f"https://{settings.gitea_domain_name}{settings.gitea_suffix}/"
        + f"{settings.gitea_org_name}/{submitter_repo_name}/"
        + f"actions/runs/{run_number}"
    )
    title, comment = joj3.generate_title_and_comment(
        score_file_path,
        actions_link,
        run_number,
        exercise_name,
        submitter,
        commit_hash,
    )
    tea.pot.gitea.create_issue(submitter_repo_name, title, comment, False)


@app.command(
    "joj3-all",
    help="run all joj3 tasks",
)
def joj3_all(
    env_path: str = Argument("", help="path to .env file"),
    score_file_path: str = Argument(
        "", help="path to score json file generated by JOJ3"
    ),
    submitter: str = Argument("", help="submitter ID"),
    repo_name: str = Argument(
        "",
        help="name of grading repo to push failed table file",
    ),
    submitter_repo_name: str = Argument(
        "",
        help="repository's name of the submitter",
    ),
    run_number: str = Argument(
        "",
        help="gitea actions run number",
    ),
    scoreboard_file_name: str = Argument(
        "scoreboard.csv", help="name of scoreboard file in the gitea repo"
    ),
    failed_table_file_name: str = Argument(
        "failed-table.md", help="name of failed table file in the gitea repo"
    ),
    exercise_name: str = Argument(
        "unknown",
        help="name of the exercise that appears on the issue title",
    ),
    commit_hash: str = Argument(
        "",
        help="commit hash that triggers gitea actions",
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
) -> None:
    set_settings(Settings(_env_file=env_path))
    set_logger(settings.stderr_log_level, diagnose=False, backtrace=False)
    logger.info(f"debug log to file: {settings.log_file_path}")
    actions_url = (
        f"https://{settings.gitea_domain_name}{settings.gitea_suffix}/"
        + f"{settings.gitea_org_name}/{submitter_repo_name}/"
        + f"actions/runs/{run_number}"
    )
    submitter_repo_url = (
        f"https://{settings.gitea_domain_name}{settings.gitea_suffix}/"
        + f"{settings.gitea_org_name}/{submitter_repo_name}"
    )
    gitea_issue_url = ""
    if not skip_result_issue:
        title, comment = joj3.generate_title_and_comment(
            score_file_path,
            actions_url,
            run_number,
            exercise_name,
            submitter,
            commit_hash,
        )
        res = tea.pot.gitea.issue_api.issue_create_issue(
            tea.pot.gitea.org_name,
            submitter_repo_name,
            body={"title": title, "body": comment},
        )
        gitea_issue_url = res["url"]
    if skip_scoreboard and skip_failed_table:
        return
    tea.pot.git  # trigger lazy load
    lock_file_path = os.path.join(
        settings.repos_dir, repo_name, settings.joj3_lock_file_path
    )
    logger.info(
        f"try to acquire lock, file path: {lock_file_path}, "
        + f"timeout: {settings.joj3_lock_file_timeout}"
    )
    with FileLock(lock_file_path, timeout=settings.joj3_lock_file_timeout).acquire():
        logger.info("file lock acquired")
        repo_path = tea.pot.git.repo_clean_and_checkout(repo_name, "grading")
        repo: Repo = tea.pot.git.get_repo(repo_name)
        if "grading" not in repo.remote().refs:
            logger.error(
                '"grading" branch not found in remote, create and push it to origin first.'
            )
            return
        if "grading" not in repo.branches:
            logger.error('"grading" branch not found in local, create it first.')
            return
        repo.git.reset("--hard", "origin/grading")
        if not skip_scoreboard:
            joj3.generate_scoreboard(
                score_file_path,
                submitter,
                os.path.join(repo_path, scoreboard_file_name),
                exercise_name,
            )
            tea.pot.git.add_commit(
                repo_name,
                [scoreboard_file_name],
                (
                    f"joj3: update scoreboard by @{submitter} in "
                    f"{settings.gitea_org_name}/{submitter_repo_name}@{commit_hash}\n\n"
                    f"gitea actions link: {actions_url}\n"
                    f"gitea issue link: {gitea_issue_url}"
                ),
            )
        if not skip_failed_table:
            joj3.generate_failed_table(
                score_file_path,
                submitter_repo_name,
                submitter_repo_url,
                os.path.join(repo_path, failed_table_file_name),
                actions_url,
            )
            tea.pot.git.add_commit(
                repo_name,
                [failed_table_file_name],
                (
                    f"joj3: update failed table by @{submitter} in "
                    f"{settings.gitea_org_name}/{submitter_repo_name}@{commit_hash}\n\n"
                    f"gitea actions link: {actions_url}"
                    f"gitea issue link: {gitea_issue_url}"
                ),
            )
        tea.pot.git.push(repo_name)


if __name__ == "__main__":
    try:
        app()
    except Exception:
        logger.exception("Unexpected error:")
