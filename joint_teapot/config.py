from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Define the settings (config).
    """

    # canvas
    canvas_domain_name: str = "oc.sjtu.edu.cn"
    canvas_suffix: str = "/"
    canvas_access_token: str = ""
    canvas_course_id: int = 0

    # gitea
    gitea_domain_name: str = "focs.ji.sjtu.edu.cn"
    gitea_suffix: str = "/git"
    gitea_access_token: str = ""
    gitea_org_name: str = ""
    gitea_debug: bool = False

    # git
    git_host: str = "ssh://git@focs.ji.sjtu.edu.cn:2222"
    repos_dir: str = "./repos"
    default_branch: str = "master"

    # mattermost
    mattermost_domain_name: str = "focs.ji.sjtu.edu.cn"
    mattermost_suffix: str = "/mm"
    mattermost_access_token: str = ""
    mattermost_team: str = ""
    mattermost_teaching_team: List[str] = [
        "charlem",
    ]

    # joj
    joj_sid: str = ""

    # joj3
    joj3_lock_file_path: str = ".git/teapot.lock"
    joj3_lock_file_timeout: int = 30

    # log file
    log_file_path: str = "joint-teapot.log"
    stderr_log_level: str = "INFO"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def set_settings(new_settings: Settings) -> None:
    for field, value in new_settings.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)


settings: Settings = get_settings()
