__version__ = "0.0.0"

from datetime import datetime
from typing import List

from loguru import logger
from typer import Typer, echo

from joint_teapot.teapot import Teapot

app = Typer(add_completion=False)
teapot = Teapot()


@app.command(
    "invite-to-teams", help="invite all canvas students to gitea teams by team name"
)
def add_all_canvas_students_to_teams(team_names: List[str]) -> None:
    teapot.add_all_canvas_students_to_teams(team_names)


@app.command(
    "create-personal", help="create personal repos on gitea for all canvas students"
)
def create_personal_repos_for_all_canvas_students() -> None:
    teapot.create_personal_repos_for_all_canvas_students()


@app.command("create-teams", help="create teams on gitea by canvas groups")
def create_teams_and_repos_by_canvas_groups() -> None:
    teapot.create_teams_and_repos_by_canvas_groups()


@app.command("get-public-keys", help="get all public keys on gitea")
def get_public_key_of_all_canvas_students() -> None:
    echo("\n".join(teapot.get_public_key_of_all_canvas_students()))


@app.command("archieve", help="clone all gitea repos to local")
def archieve_all_repos() -> None:
    teapot.archieve_all_repos()


@app.command("create-issues", help="create issues on gitea")
def create_issue_for_repos(repo_names: List[str], title: str, body: str) -> None:
    teapot.create_issue_for_repos(repo_names, title, body)


@app.command("check-issues", help="check the existence of issue by title on gitea")
def check_exist_issue_by_title(repo_names: List[str], title: str) -> None:
    echo("\n".join(teapot.check_exist_issue_by_title(repo_names, title)))


@app.command(
    "get-release",
    help="checkout git repo to git tag fetched from gitea by release name, with due date",
)
def checkout_to_repos_by_release_name(
    repo_names: List[str], release_name: str, due: datetime = datetime(3000, 1, 1)
) -> None:
    teapot.checkout_to_repos_by_release_name(repo_names, release_name, due)


if __name__ == "__main__":
    try:
        app()
    except Exception:
        logger.exception("Unexpected error:")
