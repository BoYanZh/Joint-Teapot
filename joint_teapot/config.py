from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Define the settings (config).
    """

    # canvas
    canvas_access_token: str = ""
    canvas_course_id: int = 0

    # gitea
    gitea_access_token: str = ""
    gitea_org_name: str = ""

    # git
    repos_dir: str = "./repos"

    # mattermost
    mattermost_url: str = "focs.ji.sjtu.edu.cn"
    mattermost_suffix: str = "/mm"
    mattermost_access_token: str = ""
    mattermost_team: str = ""

    # sid
    joj_sid: str = ""

    # log file
    log_file_path: str = "joint-teapot.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
