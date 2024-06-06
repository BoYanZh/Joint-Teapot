import csv
import json
import os
from datetime import datetime
from typing import Any, Dict

from joint_teapot.utils.logger import logger


def generate_scoreboard(score_file_path: str, scoreboard_file_path: str) -> None:
    if not score_file_path.endswith(".json"):
        logger.error(
            f"Score file should be a .json file, but now it is {score_file_path}"
        )
        return
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
            "last_edit",  # This is just to make changes in the file so that it can be pushed.
            # Only used in development stage. Will be removed in the future.
            "total",
        ]
        data = []

    column_updated = [False] * len(columns)  # Record wether a score has been updated
    # Update data
    with open(score_file_path) as json_file:
        scoreboard: Dict[str, Any] = json.load(json_file)

    student = f"{scoreboard['studentname']} {scoreboard['studentid']}"
    student_found = False
    for row in data:
        if row[0] == student:
            student_row = row  # This is a reference of the original data
            student_found = True
            break
    if not student_found:
        student_row = [student, "", "0"] + [""] * (
            len(columns) - 3
        )  # In formal version should be -2
        data.append(student_row)

    for stagerecord in scoreboard["stagerecords"]:
        stagename = stagerecord["stagename"]
        for stageresult in stagerecord["stageresults"]:
            name = stageresult["name"]
            for i, result in enumerate(stageresult["results"]):
                score = result["score"]
                colname = f"{stagename}/{name}"
                if len(stageresult["results"]) != 1:
                    colname = f"{colname}/{i}"
                if colname not in columns:
                    columns.append(colname)
                    column_updated.append(True)
                    for row in data:
                        row.append("")
                student_row[columns.index(colname)] = score
                column_updated[columns.index(colname)] = True
    # Score of any unupdated columns should be cleared
    for i, column in enumerate(columns):
        if column in ["", "last_edit", "total"]:
            continue
        if column_updated[i] == False:
            student_row[i] = ""

    total = 0
    for col in columns:
        if col in ["", "total", "last_edit"]:
            continue
        idx = columns.index(col)
        if (student_row[idx] is not None) and (student_row[idx] != ""):
            total += int(student_row[idx])

    student_row[columns.index("total")] = str(total)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    student_row[columns.index("last_edit")] = now  # Delete this in formal version

    # Sort data by total
    data.sort(key=lambda x: int(x[columns.index("total")]), reverse=True)

    # Write back to the csv file:
    with open(scoreboard_file_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(data)


def generate_comment(score_file_path: str) -> str:
    # TODO
    return ""
