import io
import os
import zipfile
from typing import Tuple

from colorama import Fore, Style, init
from joj_submitter import JOJSubmitter, Language

from joint_teapot.config import settings
from joint_teapot.utils.logger import logger


class JOJ:
    def __init__(self, sid: str = settings.joj_sid):
        init()
        self.submitter = JOJSubmitter(sid, logger)

    def submit_dir(self, problem_url: str, path: str, lang: str) -> Tuple[int, str]:
        if lang not in list(Language):
            raise Exception(f"unsupported language '{lang}' for JOJ")
        exclude_paths = [".git"]
        zip_buffer = io.BytesIO()
        zip_buffer.name = f"{os.path.basename(path)}.zip"
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in exclude_paths]
                for file in files:
                    zip_file.write(
                        os.path.join(root, file),
                        os.path.relpath(os.path.join(root, file), path),
                    )
        zip_buffer.seek(0)
        response = self.submitter.upload_file(problem_url, zip_buffer, lang)
        if response.status_code != 200:
            logger.error(
                f"{path} submit to JOJ error, status code {response.status_code}"
            )
            return -1, ""
        logger.info(f"{path} submit to JOJ succeed, record url {response.url}")
        record = self.submitter.get_status(response.url)
        fore_color = Fore.RED if record.status != "Accepted" else Fore.GREEN
        logger.info(
            f"status: {fore_color}{record.status}{Style.RESET_ALL}, "
            + f"accept number: {Fore.BLUE}{record.accepted_count}{Style.RESET_ALL}, "
            + f"score: {Fore.BLUE}{record.score}{Style.RESET_ALL}, "
            + f"total time: {Fore.BLUE}{record.total_time}{Style.RESET_ALL}, "
            + f"peak memory: {Fore.BLUE}{record.peak_memory}{Style.RESET_ALL}"
        )
        score_int = 0
        try:
            score_int = int(record.score)
        except ValueError:
            pass
        return score_int, response.url
