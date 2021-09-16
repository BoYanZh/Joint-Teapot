import os
import sys

from joint_teapot.utils.logger import logger

current_path = sys.path[0]
sys.path.remove(current_path)
from git import Repo

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
        logger.info("Git initialized.")

    def clone_repo(self, repo_name: str, branch: str = "master") -> Repo:
        repo_dir = os.path.join(self.repos_dir, repo_name)
        return Repo.clone_from(
            f"ssh://git@focs.ji.sjtu.edu.cn:2222/{self.org_name}/{repo_name}.git",
            repo_dir,
            branch=branch,
        )

    def get_repo(self, repo_name: str) -> Repo:
        repo_dir = os.path.join(self.repos_dir, repo_name)
        if os.path.exists(repo_dir):
            return Repo(repo_dir)
        return self.clone_repo(repo_name)

    def repo_clean_and_checkout(self, repo_name: str, checkout_dest: str) -> str:
        repo_dir = os.path.join(self.repos_dir, repo_name)
        repo = self.get_repo(repo_name)
        repo.git.fetch("--tags", "--all", "-f")
        repo.git.reset("--hard", f"origin/master")
        repo.git.clean("-d", "-f", "-x")
        repo.git.checkout(checkout_dest)
        return repo_dir
