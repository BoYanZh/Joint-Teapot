import bisect
import csv
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pydantic_settings import BaseSettings

from joint_teapot.utils.logger import logger


class Env(BaseSettings):
    github_actor: str = ""
    github_repository: str = ""
    github_sha: str = ""
    github_ref: str = ""
    github_workflow: str = ""
    github_run_number: str = "0"
    joj3_conf_name: str = ""
    joj3_groups: str = ""
    joj3_run_id: str = ""
    joj3_commit_msg: str = ""
    joj3_force_quit_stage_name: str = ""
    joj3_output_path: str = ""


def get_total_score(score_file_path: str) -> int:
    with open(score_file_path) as json_file:
        stages: List[Dict[str, Any]] = json.load(json_file)
    total_score = 0
    for stage in stages:
        for result in stage["results"]:
            total_score += result["score"]
    return total_score


def generate_scoreboard(
    score_file_path: str,
    submitter: str,
    scoreboard_file_path: str,
    exercise_name: str,
) -> None:
    if not scoreboard_file_path.endswith(".csv"):
        logger.error(
            f"Scoreboard file should be a .csv file, but now it is {scoreboard_file_path}"
        )
        return
    os.makedirs(os.path.dirname(scoreboard_file_path), exist_ok=True)
    # Load the csv file if it already exists
    if os.path.exists(scoreboard_file_path):
        with open(scoreboard_file_path, newline="") as file:
            reader = csv.reader(file)
            rows = list(reader)
        columns = rows[0]
        data = rows[1:]
    else:
        columns = [
            "",
            "last_edit",
            "total",
        ]
        data = []

    submitter_found = False
    for row in data:
        if row[0] == submitter:
            submitter_row = row  # This is a reference of the original data
            submitter_found = True
            break
    if not submitter_found:
        fixed_columns = [submitter, "", "0"]
        submitter_row = fixed_columns + [""] * (len(columns) - len(fixed_columns))
        data.append(submitter_row)

    # Update data
    with open(score_file_path) as json_file:
        stages: List[Dict[str, Any]] = json.load(json_file)

    if exercise_name == "unknown":
        for stage in stages:
            if stage["name"] != "metadata":
                continue
            comment = stage["results"][0]["comment"]
            exercise_name = comment.split("-")[0]
    # Find if exercise in table:
    if exercise_name not in columns:
        column_tail = columns[3:]
        bisect.insort(column_tail, exercise_name)
        columns[3:] = column_tail
        index = columns.index(exercise_name)
        for row in data:
            row.insert(index, "")

    exercise_total_score = 0
    for stage in stages:
        for result in stage["results"]:
            exercise_total_score += result["score"]
    exercise_total_score = exercise_total_score
    submitter_row[columns.index(exercise_name)] = str(exercise_total_score)

    total = 0
    for col in columns:
        if col in ["", "total", "last_edit"]:
            continue
        idx = columns.index(col)
        if (submitter_row[idx] is not None) and (submitter_row[idx] != ""):
            total += int(submitter_row[idx])

    submitter_row[columns.index("total")] = str(total)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    submitter_row[columns.index("last_edit")] = now

    # Sort data by total, from low to high
    data.sort(key=lambda x: int(x[columns.index("total")]))

    # Write back to the csv file:
    with open(scoreboard_file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(data)


def get_failed_table_from_file(table_file_path: str) -> List[List[str]]:
    data: List[List[str]] = []
    if os.path.exists(table_file_path):
        with open(table_file_path) as table_file:
            for i, line in enumerate(table_file):
                if i < 2:
                    continue
                stripped_line = line.strip().strip("|").split("|")
                data.append(stripped_line)
    return data


def update_failed_table_from_score_file(
    data: List[List[str]],
    score_file_path: str,
    repo_name: str,
    repo_link: str,
    action_link: str,
) -> None:
    # get info from score file
    with open(score_file_path) as json_file:
        stages: List[Dict[str, Any]] = json.load(json_file)

    failed_name = ""
    for stage in stages:
        if stage["force_quit"] == True:
            failed_name = stage["name"]
            break

    # append to failed table
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    repo = f"[{repo_name}]({repo_link})"
    failure = f"[{failed_name}]({action_link})"
    row_found = False
    for i, row in enumerate(data[:]):
        if row[1] == repo:
            row_found = True
            if failed_name == "":
                data.remove(row)
            else:
                data[i][0] = now
                data[i][2] = failure
            break
    if not row_found and failed_name != "":
        data.append([now, repo, failure])


def write_failed_table_into_file(data: List[List[str]], table_file_path: str) -> None:
    data.sort(key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M"), reverse=True)
    text = "|date|repository|failure|\n"
    text += "|----|----|----|\n"
    for row in data:
        text += f"|{row[0]}|{row[1]}|{row[2]}|\n"

    os.makedirs(os.path.dirname(table_file_path), exist_ok=True)
    with open(table_file_path, "w") as table_file:
        table_file.write(text)


def generate_failed_table(
    score_file_path: str,
    repo_name: str,
    repo_link: str,
    table_file_path: str,
    action_link: str,
) -> None:
    if not table_file_path.endswith(".md"):
        logger.error(
            f"Failed table file should be a .md file, but now it is {table_file_path}"
        )
        return

    data = get_failed_table_from_file(table_file_path)
    update_failed_table_from_score_file(
        data,
        score_file_path,
        repo_name,
        repo_link,
        action_link,
    )
    write_failed_table_into_file(data, table_file_path)


def generate_title_and_comment(
    score_file_path: str,
    action_link: str,
    run_number: str,
    exercise_name: str,
    submitter: str,
    commit_hash: str,
    submitter_in_title: bool = True,
    run_id: str = "unknown",
    max_total_score: int = -1,
    penalty_factor: float = 1.0,
) -> Tuple[str, str]:
    with open(score_file_path) as json_file:
        stages: List[Dict[str, Any]] = json.load(json_file)
    if exercise_name == "unknown":
        for stage in stages:
            if stage["name"] != "metadata":
                continue
            comment = stage["results"][0]["comment"]
            exercise_name = comment.split("-")[0]
    total_score = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    comment = (
        f"Generated at {now} from [Gitea Actions #{run_number}]({action_link}), "
        f"commit {commit_hash}, "
        f"triggered by @{submitter}, "
        f"run ID `{run_id}`.\n"
        "Powered by [JOJ3](https://github.com/joint-online-judge/JOJ3) and "
        "[Joint-Teapot](https://github.com/BoYanZh/Joint-Teapot) with ❤️.\n"
    )
    if penalty_factor != 1.0:
        comment += f"## ⚠️Total Score Penalty Warning⚠️\n**The total score is multiplied by {penalty_factor}.**\n"
    for stage in stages:
        if all(
            result["score"] == 0 and result["comment"].strip() == ""
            for result in stage["results"]
        ):
            continue
        stage_score = sum(result["score"] for result in stage["results"])
        comment += f"## {stage['name']} - Score: {stage_score}"
        force_quit = stage["force_quit"]
        if force_quit:
            comment += " - Fatal Error"
        comment += "\n"
        for i, result in enumerate(stage["results"]):
            comment += "<details>\n"
            comment += f"<summary>Case {i} - Score: {result['score']}</summary>\n"
            if result["comment"].strip() != "":
                comment += f"\n{result['comment']}\n\n"
            comment += "</details>\n\n"
            total_score += result["score"]
        comment += "\n"
    if penalty_factor != 1.0:
        total_score = round(total_score - abs(total_score) * (1 - penalty_factor))
    title = get_title_prefix(exercise_name, submitter, submitter_in_title)
    if max_total_score >= 0:
        title += f"{total_score} / {max_total_score}"
    else:
        title += f"{total_score}"
    return title, comment


def check_skipped(score_file_path: str, keyword: str) -> bool:
    with open(score_file_path) as json_file:
        stages: List[Dict[str, Any]] = json.load(json_file)
    for stage in stages:
        if stage["name"] != "metadata":
            continue
        comment = stage["results"][0]["comment"]
        if keyword in comment or "skip-teapot" in comment:
            return True
    return False


def get_title_prefix(
    exercise_name: str, submitter: str, submitter_in_title: bool
) -> str:
    title = f"JOJ3 Result for {exercise_name} by @{submitter} - Score: "
    if not submitter_in_title:
        title = f"JOJ3 Result for {exercise_name} - Score: "
    return title


def parse_penalty_config(penalty_config: str) -> List[Tuple[float, float]]:
    res = []
    for penalty in penalty_config.split(","):
        if "=" not in penalty:
            continue
        hour, factor = map(float, penalty.split("="))
        res.append((hour, factor))
    res.sort(key=lambda x: x[0])
    return res


def get_penalty_factor(
    end_time: Optional[datetime],
    penalty_config: str,
) -> float:
    if not end_time or not penalty_config:
        return 1.0
    penalties = parse_penalty_config(penalty_config)
    now = datetime.now()
    res = 0.0
    for hour, factor in penalties[::-1]:
        if now < end_time + timedelta(hours=hour):
            res = factor
        else:
            break
    return res
