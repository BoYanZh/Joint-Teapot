import os
import sys
from time import sleep
from typing import List, Optional

from joint_teapot.utils.logger import logger

current_path = sys.path[0]
sys.path.remove(current_path)
from git import Repo
from git.exc import GitCommandError
from git.remote import PushInfoList

sys.path.insert(0, current_path)

from joint_teapot.config import settings


class Git:
    def __init__(
        self,
        git_host: str = "",
        org_name: str = "",
        repos_dir: str = "",
    ):
        git_host = git_host or settings.git_host
        org_name = org_name or settings.gitea_org_name
        repos_dir = repos_dir or settings.repos_dir
        self.git_host = git_host
        self.org_name = org_name
        self.repos_dir = repos_dir
        if not os.path.isdir(self.repos_dir):
            raise Exception(f"{self.repos_dir} does not exist! Create it first.")
        logger.debug("Git initialized")
        logger.info(f"repos dir: {self.repos_dir}")

    def clone_repo(
        self, repo_name: str, branch: str = "master", auto_retry: bool = True
    ) -> Optional[Repo]:
        repo = None
        repo_dir = os.path.join(self.repos_dir, repo_name)
        retry_interval = 2
        while retry_interval and auto_retry:
            try:
                repo = Repo.clone_from(
                    f"{self.git_host}/{self.org_name}/{repo_name}.git",
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
        self,
        repo_name: str,
        checkout_dest: str,
        *,
        auto_retry: bool = True,
        clean_git_lock: bool = False,
        reset_target: str = "origin/master",
    ) -> str:
        repo_dir = os.path.join(self.repos_dir, repo_name)
        repo = self.get_repo(repo_name)
        if not repo:
            return repo_dir
        retry_interval = 2
        while retry_interval and auto_retry:
            try:
                if clean_git_lock:
                    lock_files = [
                        "index.lock",
                        "HEAD.lock",
                        "fetch-pack.lock",
                        "logs/HEAD.lock",
                        "packed-refs.lock",
                        "config.lock",
                    ]
                    for lock_file in lock_files:
                        lock_path = os.path.join(repo_dir, ".git", lock_file)
                        if os.path.exists(lock_path):
                            os.remove(lock_path)
                repo.git.fetch("--tags", "--all", "-f")
                repo.git.reset("--hard", reset_target)
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

    def add_commit(
        self, repo_name: str, files_to_add: List[str], commit_message: str
    ) -> None:
        repo: Repo = self.get_repo(repo_name)
        for file in files_to_add:
            try:
                repo.index.add(file)
            except OSError:
                logger.warning(
                    f'File path "{file}" does not exist. Skipping this file.'
                )
                continue
        if repo.is_dirty(untracked_files=True) or repo.index.diff(None):
            repo.index.commit(commit_message)

    def push(self, repo_name: str) -> PushInfoList:
        repo: Repo = self.get_repo(repo_name)
        return repo.remote(name="origin").push()
