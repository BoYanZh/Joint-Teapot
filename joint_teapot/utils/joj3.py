import csv
import json
import os
from datetime import datetime
from typing import Any, Dict

from joint_teapot.utils.logger import logger


def generate_scoreboard(
    score_file_path: str, submitter: str, scoreboard_file_path: str
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

    column_updated = [False] * len(columns)  # Record wether a score has been updated
    # Update data
    with open(score_file_path) as json_file:
        scorefile: Dict[str, Any] = json.load(json_file)

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

    for stagerecord in scorefile["stagerecords"]:
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
                submitter_row[columns.index(colname)] = score
                column_updated[columns.index(colname)] = True
    # Score of any unupdated columns should be cleared
    for i, column in enumerate(columns):
        if column in ["", "last_edit", "total"]:
            continue
        if column_updated[i] == False:
            submitter_row[i] = ""

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


def generate_comment(score_file_path: str) -> str:
    # TODO
    return ""
