import os
import sys
from time import sleep
from typing import Optional

from joint_teapot.utils.logger import logger

current_path = sys.path[0]
sys.path.remove(current_path)
from git import Repo  # type: ignore
from git.exc import GitCommandError

sys.path.insert(0, current_path)

from joint_teapot.config import settings


class Git:
    def __init__(
        self,
        org_name: str = settings.gitea_org_name,
        repos_dir: str = settings.repos_dir,
    ):
        self.org_name = org_name
        if not os.path.isdir(repos_dir):
            raise Exception(f"{repos_dir} does not exist! Create it first.")
        self.repos_dir = repos_dir
        logger.debug("Git initialized")

    def clone_repo(
        self, repo_name: str, branch: str = "master", auto_retry: bool = True
    ) -> Optional[Repo]:
        repo = None
        repo_dir = os.path.join(self.repos_dir, repo_name)
        retry_interval = 2
        while retry_interval and auto_retry:
            try:
                repo = Repo.clone_from(
                    f"ssh://git@focs.ji.sjtu.edu.cn:2222/{self.org_name}/{repo_name}.git",
                    repo_dir,
                    branch=branch,
                )
                retry_interval = 0
            except GitCommandError as e:
                if "Connection refused" in e.stderr or "Connection reset" in e.stderr:
                    logger.warning(
                        f"{repo_name} connection refused/reset in clone. "
                        "Probably by JI firewall."
                    )
                    logger.info(f"wait for {retry_interval} seconds to retry...")
                    sleep(retry_interval)
                    if retry_interval < 64:
                        retry_interval *= 2
                elif f"Remote branch {branch} not found in upstream origin" in e.stderr:
                    retry_interval = 0
                    logger.error(f"{repo_name} origin/{branch} not found")
                else:
                    raise
        return repo

    def get_repo(self, repo_name: str) -> Optional[Repo]:
        repo_dir = os.path.join(self.repos_dir, repo_name)
        if os.path.exists(repo_dir):
            return Repo(repo_dir)
        return self.clone_repo(repo_name)

    def repo_clean_and_checkout(
        self, repo_name: str, checkout_dest: str, auto_retry: bool = True
    ) -> str:
        repo_dir = os.path.join(self.repos_dir, repo_name)
        repo = self.get_repo(repo_name)
        if not repo:
            return repo_dir
        retry_interval = 2
        while retry_interval and auto_retry:
            try:
                repo.git.fetch("--tags", "--all", "-f")
                repo.git.reset("--hard", "origin/master")
                repo.git.clean("-d", "-f", "-x")
                repo.git.checkout(checkout_dest)
                retry_interval = 0
            except GitCommandError as e:
                if "Connection refused" in e.stderr or "Connection reset" in e.stderr:
                    logger.warning(
                        f"{repo_name} connection refused/reset in fetch. "
                        "Probably by JI firewall."
                    )
                    logger.info(f"wait for {retry_interval} seconds to retry...")
                    sleep(retry_interval)
                    if retry_interval < 64:
                        retry_interval *= 2
                elif "Remote branch master not found in upstream origin" in e.stderr:
                    retry_interval = 0
                    logger.error(f"{repo_name} origin/master not found")
                else:
                    raise
        return repo_dir
