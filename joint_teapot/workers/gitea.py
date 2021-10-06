import re
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional

import focs_gitea
from canvasapi.group import Group, GroupMembership
from canvasapi.paginated_list import PaginatedList
from canvasapi.user import User
from focs_gitea.rest import ApiException

from joint_teapot.config import settings
from joint_teapot.utils.logger import logger
from joint_teapot.utils.main import first


class PermissionEnum(Enum):
    read = "read"
    write = "write"
    admin = "admin"


def default_repo_name_convertor(user: User) -> Optional[str]:
    id, name = user.sis_login_id, user.name
    eng = re.sub("[\u4e00-\u9fa5]", "", name)
    eng = eng.replace(",", "")
    eng = "".join([word[0].capitalize() + word[1:] for word in eng.split()])
    return f"{eng}{id}"


def list_all(method: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    all_res = []
    page = 1
    while True:
        res = method(*args, **kwargs, page=page)
        if not res:
            break
        for item in res:
            all_res.append(item)
        page += 1
    return all_res


class Gitea:
    def __init__(
        self,
        access_token: str = settings.gitea_access_token,
        org_name: str = settings.gitea_org_name,
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
        logger.debug("Gitea initialized")

    @lru_cache()
    def _get_team_id_by_name(self, name: str) -> int:
        res = self.organization_api.team_search(self.org_name, q=str(name), limit=1)
        if len(res["data"]) == 0:
            raise Exception(f"{name} not found by name in Gitea")
        return res["data"][0]["id"]

    @lru_cache()
    def _get_username_by_canvas_student(self, student: User) -> str:
        res = self.user_api.user_search(q=student.sis_login_id, limit=1)
        if len(res["data"]) == 0:
            raise Exception(f"{student} not found in Gitea")
        return res["data"][0]["username"]

    def add_canvas_students_to_teams(
        self, students: PaginatedList, team_names: List[str]
    ) -> None:
        for team_name in team_names:
            team_id = self._get_team_id_by_name(team_name)
            team_members = self.organization_api.org_list_team_members(team_id)
            for student in students:
                try:
                    username = self._get_username_by_canvas_student(student)
                    team_member = first(team_members, lambda x: x.login == username)
                    if team_member is None:
                        self.organization_api.org_add_team_member(team_id, username)
                        logger.info(f"{student} added to team {team_name}")
                    else:
                        team_members.remove(team_member)
                        logger.warning(f"{student} already in team {team_name}")
                except Exception as e:
                    logger.error(e)
            for team_member in team_members:
                logger.error(
                    f"{team_member.full_name} found in team {team_name} "
                    + "but not found in Canvas students"
                )

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
            body = {
                "auto_init": False,
                "default_branch": "master",
                "name": repo_name,
                "private": True,
                "template": False,
                "trust_model": "default",
            }
            try:
                try:
                    repo = self.organization_api.create_org_repo(
                        self.org_name, body=body
                    )
                    logger.info(
                        f"Personal repo {self.org_name}/{repo_name} for {student} created"
                    )
                except ApiException as e:
                    if e.status == 409:
                        logger.warning(
                            f"Personal repo {self.org_name}/{repo_name} for {student} already exists"
                        )
                    else:
                        raise (e)
                username = self._get_username_by_canvas_student(student)
                self.repository_api.repo_add_collaborator(
                    self.org_name, repo_name, username
                )
            except Exception as e:
                logger.error(e)
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
        teams = list_all(self.organization_api.org_list_teams, self.org_name)
        repos = list_all(self.organization_api.org_list_repos, self.org_name)
        group: Group
        for group in groups:
            team_name = team_name_convertor(group.name)
            repo_name = repo_name_convertor(group.name)
            if team_name is None or repo_name is None:
                continue
            team = first(teams, lambda team: team.name == team_name)
            if team is None:
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
                logger.info(f"{self.org_name}/{team_name} created")
            repo = first(repos, lambda repo: repo.name == repo_name)
            if repo is None:
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
                logger.info(f"Team {team_name} created")
            self.organization_api.org_add_team_repository(
                team.id, self.org_name, repo_name
            )
            membership: GroupMembership
            student_count = 0
            for membership in group.get_memberships():
                student = first(students, lambda s: s.id == membership.user_id)
                if student is None:
                    raise Exception(
                        f"student with user_id {membership.user_id} not found"
                    )
                username = self._get_username_by_canvas_student(student)
                self.organization_api.org_add_team_member(team.id, username)
                self.repository_api.repo_add_collaborator(
                    self.org_name, repo_name, username
                )
                student_count += 1
            try:
                self.repository_api.repo_delete_branch_protection(
                    self.org_name, repo_name, "master"
                )
            except ApiException as e:
                if e.status != 404:
                    raise
            self.repository_api.repo_create_branch_protection(
                self.org_name,
                repo_name,
                body={
                    "block_on_official_review_requests": True,
                    "block_on_outdated_branch": True,
                    "block_on_rejected_reviews": True,
                    "branch_name": "master",
                    "dismiss_stale_approvals": True,
                    "enable_approvals_whitelist": False,
                    "enable_merge_whitelist": False,
                    "enable_push": False,
                    "enable_push_whitelist": False,
                    "enable_status_check": False,
                    "merge_whitelist_teams": [],
                    "merge_whitelist_usernames": [],
                    "protected_file_patterns": "",
                    "push_whitelist_deploy_keys": False,
                    "push_whitelist_teams": [],
                    "push_whitelist_usernames": [],
                    "require_signed_commits": False,
                    "required_approvals": max(student_count - 1, 0),
                    "status_check_contexts": [],
                },
            )
            logger.info(f"{self.org_name}/{repo_name} jobs done")
        return repo_names

    def get_public_key_of_canvas_students(self, students: PaginatedList) -> List[str]:
        res = []
        for student in students:
            try:
                username = self._get_username_by_canvas_student(student)
                res.extend(
                    [
                        item.key
                        for item in list_all(self.user_api.user_list_keys, username)
                    ]
                )
            except Exception as e:
                logger.error(e)
        return res

    def get_repos_releases(self, repo_names: List[str]) -> List[List[Dict[str, Any]]]:
        return [
            list_all(self.repository_api.repo_list_releases, self.org_name, repo_name)
            for repo_name in repo_names
        ]

    def get_all_repo_names(self) -> List[str]:
        return [
            data.name
            for data in list_all(self.organization_api.org_list_repos, self.org_name)
        ]

    def get_no_collaborator_repos(self) -> List[str]:
        res = []
        for data in list_all(self.organization_api.org_list_repos, self.org_name):
            collaborators = self.repository_api.repo_list_collaborators(
                self.org_name, data.name
            )
            if collaborators:
                continue
            logger.info(f"{self.org_name}/{data.name} has no collaborators")
            res.append(data.name)
        return res

    def get_no_commit_repos(self) -> List[str]:
        res = []
        for data in list_all(self.organization_api.org_list_repos, self.org_name):
            try:
                commits = self.repository_api.repo_get_all_commits(
                    self.org_name, data.name
                )
            except ApiException as e:
                if e.status == 409:
                    logger.info(f"{self.org_name}/{data.name} has no commits")
                    res.append(data.name)
                else:
                    raise (e)
        return res

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
                for item in list_all(
                    self.repository_api.repo_list_collaborators,
                    self.org_name,
                    repo_name,
                )
            ]
        self.issue_api.issue_create_issue(
            self.org_name,
            repo_name,
            body={"title": title, "body": body, "assignees": assignees},
        )

    def check_exist_issue_by_title(self, repo_name: str, title: str) -> bool:
        for issue in list_all(
            self.issue_api.issue_list_issues, self.org_name, repo_name
        ):
            if issue.title == title:
                return True
        return False

    def close_all_issues(self) -> None:
        for repo in list_all(self.organization_api.org_list_repos, self.org_name):
            for issue in list_all(
                self.issue_api.issue_list_issues, self.org_name, repo.name
            ):
                if issue.state != "closed":
                    self.issue_api.issue_edit_issue(
                        self.org_name, repo.name, issue.number, body={"state": "closed"}
                    )

    def archieve_all_repos(self) -> None:
        for repo in list_all(self.organization_api.org_list_repos, self.org_name):
            self.repository_api.repo_edit(
                self.org_name, repo.name, body={"archived": True}
            )


if __name__ == "__main__":
    gitea = Gitea()
    res = gitea.get_no_commit_repos()
