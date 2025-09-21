import re
from enum import Enum
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, TypeVar

import focs_gitea
from canvasapi.group import Group, GroupMembership
from canvasapi.paginated_list import PaginatedList
from canvasapi.user import User
from focs_gitea.rest import ApiException

from joint_teapot.config import settings
from joint_teapot.utils.logger import logger
from joint_teapot.utils.main import default_repo_name_convertor, first


class PermissionEnum(Enum):
    read = "read"
    write = "write"
    admin = "admin"


T = TypeVar("T")


def list_all(method: Callable[..., Iterable[T]], *args: Any, **kwargs: Any) -> List[T]:
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
        access_token: str = "",  # nosec
        org_name: str = "",
        domain_name: str = "",
        suffix: str = "",
    ):
        access_token = access_token or settings.gitea_access_token
        org_name = org_name or settings.gitea_org_name
        domain_name = domain_name or settings.gitea_domain_name
        suffix = suffix or settings.gitea_suffix
        self.org_name = org_name
        configuration = focs_gitea.Configuration()
        configuration.api_key["access_token"] = access_token
        configuration.host = f"https://{domain_name}{suffix}/api/v1"
        configuration.debug = settings.gitea_debug
        for v in configuration.logger.values():
            v.handlers = []
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
        res = self.organization_api.team_search(
            self.org_name, q=str(name), limit=1
        ).to_dict()
        if len(res["data"] or []) == 0:
            raise Exception(
                f"{name} not found by name in Gitea. Possible reason: you did not join this team."
            )
        return res["data"][0]["id"]

    @lru_cache()
    def _get_username_by_canvas_student(self, student: User) -> str:
        if (
            student.email is not None
            and student.email.count("@") == 1
            and student.email.endswith("@sjtu.edu.cn")
        ):
            return student.email.split("@")[0]
        raise Exception(f"Can not get username of {student}, an SJTU email is expected")

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

    def get_user(self) -> Any:
        return self.user_api.user_get_current()

    def create_personal_repos_for_canvas_students(
        self,
        students: PaginatedList,
        repo_name_convertor: Callable[
            [User], Optional[str]
        ] = default_repo_name_convertor,
        template: str = "",
    ) -> List[str]:
        repo_names = []
        for student in students:
            repo_name = repo_name_convertor(student)
            if repo_name is None:
                continue
            repo_names.append(repo_name)
            try:
                try:
                    if template == "":
                        body = {
                            "auto_init": False,
                            "default_branch": settings.default_branch,
                            "name": repo_name,
                            "private": True,
                            "template": False,
                            "trust_model": "default",
                        }
                        self.organization_api.create_org_repo(self.org_name, body=body)
                    else:
                        body = {
                            "default_branch": settings.default_branch,
                            "git_content": True,
                            "git_hooks": True,
                            "labels": True,
                            "name": repo_name,
                            "owner": self.org_name,
                            "private": True,
                            "protected_branch": True,
                        }
                        self.repository_api.generate_repo(
                            self.org_name, template, body=body
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
        template: str = "",
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
                logger.info(f"Team {team_name} created")
            if first(repos, lambda repo: repo.name == repo_name) is None:
                repo_names.append(repo_name)
                if template == "":
                    self.organization_api.create_org_repo(
                        self.org_name,
                        body={
                            "auto_init": False,
                            "default_branch": settings.default_branch,
                            "name": repo_name,
                            "private": True,
                            "template": False,
                            "trust_model": "default",
                        },
                    )
                else:
                    self.repository_api.generate_repo(
                        self.org_name,
                        template,
                        body={
                            "default_branch": settings.default_branch,
                            "git_content": True,
                            "git_hooks": True,
                            "labels": True,
                            "name": repo_name,
                            "owner": self.org_name,
                            "private": True,
                            "protected_branch": True,
                        },
                    )
                logger.info(f"{self.org_name}/{team_name} created")
            try:
                self.organization_api.org_add_team_repository(
                    team.id, self.org_name, repo_name
                )
            except Exception as e:
                logger.warning(e)
            membership: GroupMembership
            student_count = 0
            for membership in group.get_memberships():
                student = first(students, lambda s: s.id == membership.user_id)
                student_count += 1
                if student is None:
                    raise Exception(
                        f"student with user_id {membership.user_id} not found"
                    )
                try:
                    username = self._get_username_by_canvas_student(student)
                except Exception as e:
                    logger.warning(e)
                    continue
                try:
                    self.organization_api.org_add_team_member(team.id, username)
                    self.repository_api.repo_add_collaborator(
                        self.org_name, repo_name, username
                    )
                except Exception as e:
                    logger.error(e)
                    continue
            try:
                self.repository_api.repo_delete_branch_protection(
                    self.org_name, repo_name, settings.default_branch
                )
            except ApiException as e:
                if e.status != 404:
                    raise
            try:
                self.repository_api.repo_create_branch_protection(
                    self.org_name,
                    repo_name,
                    body={
                        "block_on_official_review_requests": True,
                        "block_on_outdated_branch": True,
                        "block_on_rejected_reviews": True,
                        "branch_name": settings.default_branch,
                        "dismiss_stale_approvals": True,
                        "enable_approvals_whitelist": False,
                        "enable_merge_whitelist": False,
                        "enable_push": True,
                        "enable_push_whitelist": True,
                        "merge_whitelist_teams": [],
                        "merge_whitelist_usernames": [],
                        "protected_file_patterns": "",
                        "push_whitelist_deploy_keys": False,
                        "push_whitelist_teams": ["Owners"],
                        "push_whitelist_usernames": [],
                        "require_signed_commits": False,
                        "required_approvals": max(student_count - 1, 0),
                        "enable_status_check": True,
                        "status_check_contexts": ["Run JOJ3 on Push / run (push)"],
                    },
                )
            except ApiException as e:
                if e.status != 404:
                    raise
            logger.info(f"{self.org_name}/{repo_name} jobs done")
        return repo_names

    def get_public_key_of_canvas_students(
        self, students: PaginatedList
    ) -> Dict[str, List[str]]:
        res = {}
        for student in students:
            try:
                username = self._get_username_by_canvas_student(student)
                keys = [
                    item.key
                    for item in list_all(self.user_api.user_list_keys, username)
                ]
                if not keys:
                    logger.info(f"{student} has not uploaded ssh keys to gitea")
                    continue
                res[student.login_id] = keys
            except Exception as e:
                logger.error(e)
        return res

    def get_repo_releases(self, repo_name: str) -> List[Any]:
        try:
            args = self.repository_api.repo_list_releases, self.org_name, repo_name
            return list_all(*args)
        except ApiException as e:
            if e.status != 404:
                raise
        return []

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

    def get_repos_status(self) -> Dict[str, Tuple[int, int]]:
        res = {}
        for repo in list_all(self.organization_api.org_list_repos, self.org_name):
            commits = []
            issues = []
            try:
                commits = self.repository_api.repo_get_all_commits(
                    self.org_name, repo.name
                )
            except ApiException as e:
                if e.status != 409:
                    raise
            issues = self.issue_api.issue_list_issues(
                self.org_name, repo.name, state="all"
            )
            # if not commits:
            #     logger.info(f"{self.org_name}/{repo.name} has no commits")
            res[repo.name] = (len(commits), len(issues))
        return res

    def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str,
        assign_every_collaborators: bool = True,
        milestone: str = "",
        labels: list[str] = [],
    ) -> None:
        assignees = []
        if assign_every_collaborators:
            assignees = [
                item.login
                for item in list_all(
                    self.repository_api.repo_list_collaborators,
                    self.org_name,
                    repo_name,
                )
            ]
        milestone_id = None
        if milestone:
            milestone_list = self.issue_api.issue_get_milestones_list(
                self.org_name, repo_name
            )
            if milestone not in [m.title for m in milestone_list]:
                logger.warning(f"Milestone {milestone} does not exist in {repo_name}")
            else:
                milestone_id = first(
                    [m.id for m in milestone_list if m.title == milestone]
                )
        labels_id = []
        if labels:
            labels_list = self.issue_api.issue_list_labels(self.org_name, repo_name)
            labels_id = [l.id for l in labels_list if l.name in labels]
            if not labels_id:
                logger.warning(f"no label matches {labels}")
        self.issue_api.issue_create_issue(
            self.org_name,
            repo_name,
            body={
                "title": title,
                "body": body,
                "assignees": assignees,
                "milestone": milestone_id,
                "labels": labels_id,
            },
        )
        logger.info(f'Created issue "{title}" in {repo_name}')

    def create_comment(
        self,
        repo_name: str,
        index: int,
        body: str,
    ) -> None:
        self.issue_api.issue_create_comment(
            self.org_name,
            repo_name,
            index,
            body={"body": body},
        )
        logger.info(f"Created comment in {repo_name}/issues/{index}")

    def create_milestone(
        self,
        repo_name: str,
        title: str,
        description: str,
        due_on: str,
    ) -> None:
        if due_on == "":
            self.issue_api.issue_create_milestone(
                self.org_name,
                repo_name,
                body={"title": title, "description": description},
            )
            return
        self.issue_api.issue_create_milestone(
            self.org_name,
            repo_name,
            body={
                "title": title,
                "description": description,
                "due_on": due_on + "T23:59:59.999+08:00",
            },
        )

    def check_exist_issue_by_title(self, repo_name: str, title: str) -> bool:
        for issue in list_all(
            self.issue_api.issue_list_issues, self.org_name, repo_name
        ):
            if issue.title == title:
                return True
        return False

    def close_all_issues(self) -> None:
        for repo_name in self.get_all_repo_names():
            issues = list_all(
                self.issue_api.issue_list_issues, self.org_name, repo_name
            )
            for issue in issues:
                if issue.state != "closed":
                    self.issue_api.issue_edit_issue(
                        self.org_name, repo_name, issue.number, body={"state": "closed"}
                    )

    def archive_repos(self, regex: str = ".+", dry_run: bool = True) -> None:
        if dry_run:
            logger.info("Dry run enabled. No changes will be made to the repositories.")
        logger.info(f"Archiving repos with name matching {regex}")
        for repo_name in self.get_all_repo_names():
            if re.fullmatch(regex, repo_name):
                logger.info(f"Archived {repo_name}")
                if not dry_run:
                    self.repository_api.repo_edit(
                        self.org_name, repo_name, body={"archived": True}
                    )

    def unwatch_all_repos(self) -> None:
        for repo in list_all(self.organization_api.org_list_repos, self.org_name):
            self.repository_api.user_current_delete_subscription(
                self.org_name, repo.name
            )

    def get_all_teams(self) -> Dict[str, List[str]]:
        res: Dict[str, List[str]] = {}
        for team in list_all(self.organization_api.org_list_teams, self.org_name):
            if team.name == "Owners":
                continue
            team_id = team.id
            try:
                members = [
                    m.login.lower()
                    for m in self.organization_api.org_list_team_members(team_id)
                ]
            except ApiException as e:
                logger.warning(
                    f"Failed to get members of team {team_id} in {self.org_name}: {e}"
                )
                continue
            res[team.name] = members
        return res

    def unsubscribe_from_repos(self, pattern: str) -> None:
        subscriptions = [
            sub
            for sub in self.user_api.user_current_list_subscriptions()
            if sub.owner.login == self.org_name
            and re.search(pattern, sub.name) is not None
        ]
        if len(subscriptions) == 0:
            logger.warning(f"No subscribed repo matches the pattern {pattern}")
            return
        logger.info(
            f"{len(subscriptions)} subscriptions match the pattern {pattern}: {[s.name for s in subscriptions]}"
        )
        for sub in subscriptions:
            self.repository_api.user_current_delete_subscription(
                self.org_name, sub.name
            )
            logger.info(f"Unsubscribed from {sub.name}")

    def create_milestones(
        self, milestone: str, regex: str, due_date: str, description: str
    ) -> None:
        for repo_name in self.get_all_repo_names():
            if not re.fullmatch(regex, repo_name):
                continue
            milestone_list = self.issue_api.issue_get_milestones_list(
                self.org_name, repo_name
            )
            if milestone in [m.title for m in milestone_list]:
                logger.warning(f"Milestone {milestone} already exists in {repo_name}")
                continue
            self.create_milestone(repo_name, milestone, description, due_date)
            logger.info(f"Created milestone {milestone} in {repo_name}")


if __name__ == "__main__":
    gitea = Gitea()
