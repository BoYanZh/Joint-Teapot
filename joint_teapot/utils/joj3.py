import bisect
import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from joint_teapot.utils.logger import logger


def generate_scoreboard(
    score_file_path: str, submitter: str, exercise_name: str, scoreboard_file_path: str
) -> None:
    if not scoreboard_file_path.endswith(".csv"):
        logger.error(
            f"Scoreboard file should be a .csv file, but now it is {scoreboard_file_path}"
        )
        return

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
            "last_edit",  # FIXME:
            # This is just to make changes in the file so that it can be pushed.
            # Only used in development stage. Will be removed in the future.
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
        submitter_row = [submitter, "", "0"] + [""] * (
            len(columns) - 3
        )  # FIXME: In formal version should be -2
        data.append(submitter_row)

    # Find if exercise in table:
    if exercise_name not in columns:
        column_tail = columns[3:]
        bisect.insort(column_tail, exercise_name)
        columns[3:] = column_tail
        index = columns.index(exercise_name)
        for row in data:
            row.insert(index, "")

    # Update data
    with open(score_file_path) as json_file:
        scorefile: List[Dict[str, Any]] = json.load(json_file)

    exercise_total_score = 0
    for stage in scorefile:
        for result in stage["results"]:
            exercise_total_score += result["score"]
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
    submitter_row[
        columns.index("last_edit")
    ] = now  # FIXME: Delete this in formal version

    # Sort data by total
    data.sort(key=lambda x: int(x[columns.index("total")]), reverse=True)

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
    data: List[List[str]], score_file_path: str, repo_name: str, repo_link: str
) -> None:
    # get info from score file
    with open(score_file_path) as json_file:
        scorefile: List[Dict[str, Any]] = json.load(json_file)

    failed_name = ""
    for stage in scorefile:
        if stage["force_quit"] == True:
            failed_name = stage["name"]
            break

    # append to failed table
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    repo = f"[{repo_name}]({repo_link})"
    failure = f"[{failed_name}]({'#'})"  # TODO: Update failure link
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
    data = sorted(data, key=lambda x: x[1])
    text = "|date|repository|failure|\n"
    text += "|----|----|----|\n"
    for row in data:
        text += f"|{row[0]}|{row[1]}|{row[2]}|\n"

    with open(table_file_path, "w") as table_file:
        table_file.write(text)


def generate_failed_table(
    score_file_path: str, repo_name: str, repo_link: str, table_file_path: str
) -> None:
    if not table_file_path.endswith(".md"):
        logger.error(
            f"Failed table file should be a .md file, but now it is {table_file_path}"
        )
        return

    data = get_failed_table_from_file(table_file_path)
    update_failed_table_from_score_file(data, score_file_path, repo_name, repo_link)
    write_failed_table_into_file(data, table_file_path)


def generate_comment(score_file_path: str) -> str:
    # TODO
    return ""
