from typing import Dict, List

import focs_gitea
from canvasapi.paginated_list import PaginatedList
from mattermostdriver import Driver

from joint_teapot.config import settings
from joint_teapot.utils.logger import logger
from joint_teapot.workers.gitea import Gitea


class Mattermost:
    def __init__(
        self,
        access_token: str = "",  # nosec
        team_name: str = "",
        domain_name: str = "",
        suffix: str = "",
    ):
        access_token = access_token or settings.mattermost_access_token
        team_name = team_name or settings.mattermost_team
        domain_name = domain_name or settings.mattermost_domain_name
        suffix = suffix or settings.mattermost_suffix
        self.url = domain_name
        self.url_suffix = suffix
        self.endpoint = Driver(
            {
                "url": domain_name,
                "port": 443,
                "basepath": suffix + "/api/v4",
                "token": access_token,
            }
        )
        try:
            operator = self.endpoint.login()
        except Exception:
            logger.error("Cannot login to Mattermost")
            return
        if "admin" not in operator["roles"] and "system_user" not in operator["roles"]:
            logger.error("Please make sure you have enough permission")
        try:
            self.team = self.endpoint.teams.get_team_by_name(team_name)
        except Exception as e:
            logger.error(f"Cannot get team {team_name}: {e}")
            return

    def create_channels_for_groups(
        self,
        groups: Dict[str, List[str]],
        suffix: str = "",
        invite_teaching_team: bool = True,
    ) -> None:
        for group_name, members in groups.items():
            channel_name = group_name + suffix
            try:
                channel = self.endpoint.channels.create_channel(
                    {
                        "team_id": self.team["id"],
                        "name": channel_name,
                        "display_name": channel_name,
                        "type": "P",  # create private channels
                    }
                )
                logger.info(f"Added group {channel_name} to Mattermost")
            except Exception as e:
                logger.warning(
                    f"Error when creating channel {channel_name}: {e} Perhaps channel already exists?"
                )
                continue
            if invite_teaching_team:
                members.extend(settings.mattermost_teaching_team)
            for member in members:
                try:
                    mmuser = self.endpoint.users.get_user_by_username(member)
                except Exception:
                    logger.warning(
                        f"User {member} is not found on the Mattermost server"
                    )
                    self.endpoint.posts.create_post(
                        {
                            "channel_id": channel["id"],
                            "message": f"User {member} is not found on the Mattermost server",
                        }
                    )
                    continue
                # code for adding student to mm, disabled since there is no need to do that
                # try:
                #     mmuser = self.endpoint.users.create_user({'email':f"{member}@sjtu.edu.cn", 'username':member, auth_service:"gitlab"})
                # except e:
                #     logger.error(f"Error creating user {member}")
                #     continue
                try:
                    self.endpoint.channels.add_user(
                        channel["id"], {"user_id": mmuser["id"]}
                    )
                except Exception:
                    logger.warning(f"User {member} is not in the team")
                    self.endpoint.posts.create_post(
                        {
                            "channel_id": channel["id"],
                            "message": f"User {member} is not in the team",
                        }
                    )
                logger.info(f"Added member {member} to channel {channel_name}")

    def create_channels_for_individuals(
        self,
        students: PaginatedList,
        invite_teaching_team: bool = True,
    ) -> None:
        for student in students:
            display_name = student.name
            channel_name = student.sis_id
            try:
                channel = self.endpoint.channels.create_channel(
                    {
                        "team_id": self.team["id"],
                        "name": channel_name,
                        "display_name": display_name,
                        "type": "P",  # create private channels
                    }
                )
                logger.info(
                    f"Added channel {display_name} ({channel_name}) to Mattermost"
                )
            except Exception as e:
                logger.warning(
                    f"Error when creating channel {channel_name}: {e} Perhaps channel already exists?"
                )
                continue
            members = [student.login_id]
            if invite_teaching_team:
                members.extend(settings.mattermost_teaching_team)
            for member in members:
                try:
                    mmuser = self.endpoint.users.get_user_by_username(member)
                except Exception:
                    logger.warning(
                        f"User {member} is not found on the Mattermost server"
                    )
                    self.endpoint.posts.create_post(
                        {
                            "channel_id": channel["id"],
                            "message": f"User {member} is not found on the Mattermost server",
                        }
                    )
                    continue
                # code for adding student to mm, disabled since there is no need to do that
                # try:
                #     mmuser = self.endpoint.users.create_user({'email':f"{member}@sjtu.edu.cn", 'username':member, auth_service:"gitlab"})
                # except e:
                #     logger.error(f"Error creating user {member}")
                #     continue
                try:
                    self.endpoint.channels.add_user(
                        channel["id"], {"user_id": mmuser["id"]}
                    )
                except Exception:
                    logger.warning(f"User {member} is not in the team")
                    self.endpoint.posts.create_post(
                        {
                            "channel_id": channel["id"],
                            "message": f"User {member} is not in the team",
                        }
                    )

                logger.info(f"Added member {member} to channel {channel_name}")

    def create_webhooks_for_repos(
        self, repos: List[str], gitea: Gitea, gitea_suffix: bool
    ) -> None:
        # one group corresponds to one repo so these concepts can be used interchangeably
        for repo in repos:
            channel_name = f"{repo}-gitea" if gitea_suffix else repo
            logger.info(
                f"Creating webhooks for repo {gitea.org_name}/{repo} and channel {channel_name}"
            )
            try:
                mm_channel = self.endpoint.channels.get_channel_by_name(
                    self.team["id"], channel_name
                )
            except Exception as e:
                logger.warning(
                    f"Error when getting channel {channel_name} from Mattermost team {self.team['name']}: {e}"
                )
                continue
            try:
                mm_webhook = self.endpoint.webhooks.create_incoming_hook(
                    {
                        "channel_id": mm_channel["id"],
                        "display_name": f"Gitea integration for {self.team['name']}/{repo}",
                        "channel_locked": True,
                    }
                )
            except Exception as e:
                logger.error(f"Error when creating incoming webhook at Mattermost: {e}")
                continue
            try:
                gitea.repository_api.repo_create_hook(
                    gitea.org_name,
                    repo,
                    body=focs_gitea.CreateHookOption(
                        active=True,
                        type="slack",
                        events=[
                            "issues_only",
                            "issue_comment",
                            "issue_assign",
                            "pull_request_only",
                            "pull_request_comment",
                            "pull_request_review",
                            "pull_request_review_request",
                            "push",
                            "create",
                            "delete",
                            "release",
                            "wiki",
                        ],
                        config={
                            "url": f"https://{self.url}{self.url_suffix}/hooks/{mm_webhook['id']}",
                            "username": "FOCS Gitea",
                            "icon_url": f"https://{self.url}{self.url_suffix}/api/v4/brand/image",
                            "content_type": "json",
                            "channel": channel_name,
                        },
                    ),
                )
            except Exception as e:
                logger.warning(f"Error when creating outgoing webhook at Gitea: {e}")

    # unused since we can give students invitation links instead
    def invite_students_to_team(self, students: List[str]) -> None:
        for student in students:
            try:
                mmuser = self.endpoint.users.get_user_by_username(student)
            except Exception:
                logger.warning(f"User {student} is not found on the Mattermost server")
                continue
            self.endpoint.teams.add_user_to_team(
                self.team["id"], {"user_id": mmuser["id"], "team_id": self.team["id"]}
            )
            logger.info(f"Added user {student} to team {self.team['name']}")
