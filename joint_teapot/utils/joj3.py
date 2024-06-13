from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from joint_teapot.utils.logger import logger


class Failed_Table:
    class Row:
        class Link:
            def __init__(self) -> None:
                self.text: str = ""
                self.url: str = ""

            def init(self, text: str, url: str) -> Failed_Table.Row.Link:
                self.text = text
                self.url = url
                return self

            def init_from_string(self, s: str) -> Failed_Table.Row.Link:
                if s[0] == "[":
                    self.text = s[s.index("[") + 1 : s.index("]")]
                    self.url = s[s.index("(") + 1 : s.index(")")]
                else:
                    self.text = s
                return self

            def __eq__(self, other: object) -> bool:
                if isinstance(other, Failed_Table.Row.Link):
                    if self.text == other.text and self.url == other.url:
                        return True
                return False

            def __str__(self) -> str:
                if self.url == "":
                    return self.text
                else:
                    return f"[{self.text}]({self.url})"

        def __init__(self) -> None:
            self.date = ""
            self.repository = self.Link()
            self.failure = self.Link()

        def init(
            self,
            date: str,
            repo_name: str,
            repo_link: str,
            failure_name: str,
            failure_link: str,
        ) -> Failed_Table.Row:
            self.date = date
            self.repository.init(repo_name, repo_link)
            self.failure.init(failure_name, failure_link)
            return self

        def init_from_line(self, line: list[str]) -> Failed_Table.Row:
            self.date = line[0]
            self.repository.init_from_string(line[1])
            self.failure.init_from_string(line[2])
            return self

        def __str__(self) -> str:
            return f"|{self.date}|{str(self.repository)}|{str(self.failure)}|\n"

    rows: list[Row] = []

    def __init__(self, table_file_path: str) -> None:
        if os.path.exists(table_file_path):
            with open(table_file_path) as table_file:
                for i, line in enumerate(table_file):
                    if i < 2:
                        continue
                    stripped_line = line.strip()[1:-1].split("|")
                    self.rows.append(self.Row().init_from_line(stripped_line))

    def append(
        self, repo_name: str, repo_link: str, failure_name: str, failure_link: str
    ) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        search_repo = self.Row.Link().init(repo_name, repo_link)
        row_found = False
        for i, row in enumerate(self.rows[:]):
            if row.repository == search_repo:
                row_found = True
                if failure_name == "":
                    self.rows.remove(row)
                else:
                    self.rows[i].date = now
                    self.rows[i].failure = self.Row.Link().init(
                        failure_name, failure_link
                    )
                break
        if not row_found and failure_name != "":
            self.rows.append(
                self.Row().init(now, repo_name, repo_link, failure_name, failure_link)
            )

    def append_from_score_file(
        self, score_file_path: str, repo_name: str, repo_link: str
    ) -> None:
        with open(score_file_path) as json_file:
            scorefile: dict[str, Any] = json.load(json_file)
        failed_name = ""
        fail_found = False
        for testrecord in scorefile["testrecords"]:
            if fail_found:
                break
            testname = testrecord["testname"]
            for result in testrecord["stageresults"]:
                name = result["name"]
                if result["force_quit"] == True:
                    failed_name = f"{testname}/{name}"
                    fail_found = True

        self.append(repo_name, repo_link, failed_name, "")
        # TODO: What is failed_link?

    def write_into_file(self, table_file_path: str) -> None:
        self.rows = sorted(self.rows, key=lambda x: x.repository.text)
        text = "|date|repository|failure|\n"
        text += "|----|----|----|\n"
        for row in self.rows:
            text += str(row)

        with open(table_file_path, "w") as table_file:
            table_file.write(text)


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
        scorefile: dict[str, Any] = json.load(json_file)

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

    for testrecord in scorefile["testrecords"]:
        testname = testrecord["testname"]
        for stageresult in testrecord["stageresults"]:
            name = stageresult["name"]
            for i, result in enumerate(stageresult["results"]):
                score = result["score"]
                colname = f"{testname}/{name}"
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


def generate_failed_table(
    score_file_path: str, repo_name: str, repo_link: str, table_file_path: str
) -> None:
    if not table_file_path.endswith(".md"):
        logger.error(
            f"Failed table file should be a .md file, but now it is {table_file_path}"
        )
        return

    failed_table = Failed_Table(table_file_path)
    failed_table.append_from_score_file(score_file_path, repo_name, repo_link)
    failed_table.write_into_file(table_file_path)


def generate_comment(score_file_path: str) -> str:
    # TODO
    return ""
