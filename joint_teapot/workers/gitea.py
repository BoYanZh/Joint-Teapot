import re
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional

import focs_gitea
from canvasapi.group import Group, GroupMembership
from canvasapi.paginated_list import PaginatedList
from canvasapi.user import User

from joint_teapot.config import settings
from joint_teapot.utils import first


class PermissionEnum(Enum):
    read = "read"
    write = "write"
    admin = "admin"


def default_repo_name_convertor(user: User) -> Optional[str]:
    id, name = user.sis_login_id, user.sortable_name
    eng = re.sub("[\u4e00-\u9fa5]", "", name)
    eng = "".join([word[0].capitalize() + word[1:] for word in eng.split()])
    return f"{eng}{id}"


class Gitea:
    def __init__(
        self,
        access_token: str = settings.gitea_access_token,
        org_name: str = settings.org_name,
    ):
        self.org_name = org_name
        configuration = focs_gitea.Configuration()
        configuration.api_key["access_token"] = access_token
        self.api_client = focs_gitea.ApiClient(configuration)
        self.admin_api = focs_gitea.AdminApi(self.api_client)
        self.miscellaneous_api = focs_gitea.MiscellaneousApi(self.api_client)
        self.organization_api = focs_gitea.OrganizationApi(self.api_client)
        self.issue_api = focs_gitea.IssueApi(self.api_client)
        self.repository_api = focs_gitea.RepositoryApi(self.api_client)
        self.settings_api = focs_gitea.SettingsApi(self.api_client)
        self.user_api = focs_gitea.UserApi(self.api_client)

    @lru_cache
    def _get_team_id_by_name(self, name: str) -> int:
        res = self.organization_api.team_search(self.org_name, q=str(name), limit=1)
        if len(res["data"]) == 0:
            raise Exception("Team not found by name")
        return res["data"][0]["id"]

    @lru_cache
    def _get_username_by_canvas_student(self, student: User) -> str:
        res = self.user_api.user_search(q=student.sis_login_id, limit=1)
        return res["data"][0]["username"]

    def add_canvas_students_to_teams(
        self, students: PaginatedList, team_names: List[str]
    ) -> None:
        for team_name in team_names:
            team_id = self._get_team_id_by_name(team_name)
            for student in students:
                username = self._get_username_by_canvas_student(student)
                self.organization_api.org_add_team_member(team_id, username)

    def create_personal_repos_for_canvas_students(
        self,
        students: PaginatedList,
        repo_name_convertor: Callable[
            [User], Optional[str]
        ] = default_repo_name_convertor,
    ) -> List[str]:
        repo_names = []
        for student in students:
            repo_name = repo_name_convertor(student)
            if repo_name is None:
                continue
            repo_names.append(repo_name)
            repo = self.organization_api.create_org_repo(
                self.org_name,
                body={
                    "auto_init": False,
                    "default_branch": "master",
                    "name": repo_name,
                    "private": True,
                    "template": False,
                    "trust_model": "default",
                },
            )
            self.repository_api.repo_add_collaborator(
                self.org_name, repo.name, self._get_username_by_canvas_student(student)
            )
        return repo_names

    def create_teams_and_repos_by_canvas_groups(
        self,
        students: PaginatedList,
        groups: PaginatedList,
        team_name_convertor: Callable[[str], Optional[str]] = lambda name: name,
        repo_name_convertor: Callable[[str], Optional[str]] = lambda name: name,
        permission: PermissionEnum = PermissionEnum.write,
    ) -> List[str]:
        repo_names = []
        group: Group
        for group in groups:
            team_name = team_name_convertor(group.name)
            repo_name = repo_name_convertor(group.name)
            if team_name is None or repo_name is None:
                continue
            repo_names.append(repo_name)
            team = self.organization_api.org_create_team(
                self.org_name,
                body={
                    "can_create_org_repo": False,
                    "includes_all_repositories": False,
                    "name": team_name,
                    "permission": permission.value,
                    "units": [
                        "repo.code",
                        "repo.issues",
                        "repo.ext_issues",
                        "repo.wiki",
                        "repo.pulls",
                        "repo.releases",
                        "repo.projects",
                        "repo.ext_wiki",
                    ],
                },
            )
            repo = self.organization_api.create_org_repo(
                self.org_name,
                body={
                    "auto_init": False,
                    "default_branch": "master",
                    "name": repo_name,
                    "private": True,
                    "template": False,
                    "trust_model": "default",
                },
            )
            self.organization_api.org_add_team_repository(
                team.id, self.org_name, repo_name
            )
            membership: GroupMembership
            for membership in group.get_memberships():
                student = first(students, lambda s: s.id == membership.user_id)
                if student is None:
                    raise Exception(
                        f"student with user_id {membership.user_id} not found"
                    )
                username = self._get_username_by_canvas_student(student)
                self.organization_api.org_add_team_member(team.id)
                self.repository_api.repo_add_collaborator(
                    self.org_name, repo_name, username
                )
        return repo_names

    def get_public_key_of_canvas_students(
        self, students: PaginatedList
    ) -> List[List[Dict[str, Any]]]:
        return [
            self.user_api.user_list_keys(self._get_username_by_canvas_student(student))
            for student in students
        ]

    def get_repos_releases(self, repo_names: List[str]) -> List[List[Dict[str, Any]]]:
        return [
            self.repository_api.repo_list_releases(self.org_name, repo_name)
            for repo_name in repo_names
        ]

    def get_all_repo_names(self) -> List[str]:
        return [
            data.name for data in self.organization_api.org_list_repos(self.org_name)
        ]

    def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str,
        assign_every_collaborators: bool = True,
    ) -> None:
        assignees = []
        if assign_every_collaborators:
            assignees = [
                item.username
                for item in self.repository_api.repo_list_collaborators(
                    self.org_name, repo_name
                )
            ]
        self.issue_api.issue_create_issue(
            self.org_name,
            repo_name,
            body={"title": title, "body": body, "assignees": assignees},
        )

    def check_exist_issue_by_title(self, repo_name: str, title: str) -> bool:
        for issue in self.issue_api.issue_list_issues(self.org_name, repo_name):
            if issue.title == title:
                return True
        return False


if __name__ == "__main__":
    gitea = Gitea()
