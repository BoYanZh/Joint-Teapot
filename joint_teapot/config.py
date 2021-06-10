from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Define the settings (config).

    The selected value is determined as follows (in descending order of priority):
    1. The command line arguments, e.g., '--db-host' is mapped to 'db-host'
    2. Environment variables, e.g., '$DB_HOST' is mapped to 'db-host'
    3. Variables loaded from a dotenv (.env) file
    4. The default field values for the Settings model
    """

    # canvas
    canvas_access_token: str = ""
    course_id: int = 0

    # gitea
    gitea_access_token: str = ""
    org_name: str = ""

    # git
    repos_dir: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
