from datetime import datetime
from pathlib import Path
from typing import List

from typer import Argument, Typer, echo

from joint_teapot.teapot import Teapot
from joint_teapot.utils.logger import logger

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
def create_personal_repos_for_all_canvas_students() -> None:
    tea.pot.create_personal_repos_for_all_canvas_students()


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
def create_issue_for_repos(repo_names: List[str], title: str, body: str) -> None:
    tea.pot.create_issue_for_repos(repo_names, title, body)


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
def create_channels_on_mm(prefix: str = Argument("")) -> None:
    groups = [
        group
        for group in tea.pot.gitea.get_all_teams()
        if isinstance(group["name"], str) and group["name"].startswith(prefix)
    ]
    logger.info(
        f"{len(groups)} channels to be created: {groups[0]['name']} ... {groups[-1]['name']}"
    )
    tea.pot.mattermost.create_channels_for_groups(groups)


@app.command(
    "create-webhooks-for-mm",
    help="create a pair of webhooks on gitea and mm for all student groups on gitea, "
    "and configure them so that updates on gitea will be pushed to the mm channel",
)
def create_webhooks_for_mm(prefix: str = Argument("")) -> None:
    groups = [
        group["name"]
        for group in tea.pot.gitea.get_all_teams()
        if isinstance(group["name"], str) and group["name"].startswith(prefix)
    ]
    logger.info(f"{len(groups)} pairs to be created: {groups[0]} ... {groups[-1]}")
    tea.pot.mattermost.create_webhooks_for_repos(groups, tea.pot.gitea)


if __name__ == "__main__":
    try:
        app()
    except Exception:
        logger.exception("Unexpected error:")
