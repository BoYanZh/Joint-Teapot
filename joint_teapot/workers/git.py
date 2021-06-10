import os

from git import Repo

from joint_teapot.config import settings


class Git:
    def __init__(
        self, org_name: str = settings.org_name, repos_dir: str = settings.repos_dir
    ):
        self.org_name = org_name
        if not os.path.isdir(repos_dir):
            raise Exception(f"{repos_dir} does not exist! Create it first.")
        self.repos_dir = repos_dir

    def clone_repo(self, repo_name: str) -> Repo:
        repo_dir = os.path.join(self.repos_dir, repo_name)
        return Repo.clone_from(
            f"https://focs.ji.sjtu.edu.cn/git/{self.org_name}/{repo_name}",
            repo_dir,
            branch="master",
        )

    def get_repo(self, repo_name: str) -> Repo:
        repo_dir = os.path.join(self.repos_dir, repo_name)
        if os.path.exists(repo_dir):
            return Repo(repo_dir)
        return self.clone_repo(repo_dir)

    def repo_clean_and_checkout(self, repo_name: str, checkout_dest: str) -> str:
        repo_dir = os.path.join(self.repos_dir, repo_name)
        repo = self.get_repo(repo_name)
        repo.git.fetch("--tags", "--all", "-f")
        repo.git.reset("--hard", f"origin/master")
        repo.git.clean("-d", "-f", "-x")
        repo.git.checkout(checkout_dest)
        return repo_dir
