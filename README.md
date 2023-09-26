# Joint Teapot

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/352635b2c8534b0086b5a153db7c82e9)](https://app.codacy.com/gh/BoYanZh/Joint-Teapot?utm_source=github.com&utm_medium=referral&utm_content=BoYanZh/Joint-Teapot&utm_campaign=Badge_Grade_Settings)

A handy tool for TAs in JI to handle works through [Gitea](https://focs.ji.sjtu.edu.cn/git/), [Canvas](https://umjicanvas.com/), [JOJ](https://joj.sjtu.edu.cn/) and [Mattermost](https://focs.ji.sjtu.edu.cn/mm/). Joint is related to JI and also this tool which join websites together. Teapot means to hold Gitea, inspired by [@nichujie](https://github.com/nichujie).

This tool is still under heavy development. The docs may not be updated on time, and all the features are provided with the probability to change.

## Getting Started

### Setup venv (Optional)

```bash
python3 -m venv env # you only need to do that once
# each time when you need this venv, if on Linux / macOS use
source env/bin/activate
# or this if on Windows
source env/Scripts/activate
```

### Install

```bash
pip3 install -e .
cp .env.example .env && vi .env # configure environment
joint-teapot --help
```

### For developers

```bash
pip3 install -r requirements-dev.txt
pre-commit install
pytest -svv
```

## Commands & Features

### `archive-all-repos`

archive all repos in gitea organization

### `check-issues`

check the existence of issue by title on gitea

### `checkout-releases`

checkout git repo to git tag fetched from gitea by release name, with due date

### `clone-all-repos`

clone all gitea repos to local

### `close-all-issues`

close all issues and pull requests in gitea organization

### `create-channels-on-mm`

create channels for student groups according to group information on gitea. Optionally specify a prefix to ignore all repos whose names do not start with it. Optionally specify a suffix to add to all channels created.

Example: `python3 -m joint_teapot create-channels-on-mm --prefix p1 --suffix -private --invite-teaching-team` will fetch all repos whose names start with `"p1"` and create channels on mm for these repos like "p1team1-private". Members of a repo will be added to the corresponding channel. And teaching team (maybe adjust `mattermost_teaching_team` list in `./joint_teapot/config.py`) will be invited to the channels.

### `create-issues`

create issues on gitea. Specify a list of repos (use `--regex` to match against list of patterns), a title, and a body (use `--file` to read from file), in this order.

Examples (run both with `python3 -m joint_teapot create-issues`):

- `pgroup-08 pgroup-17 "Hurry up" "You are running out of time"` will create an issue in these two pgroups.
- `--regex "^pgroup" "Final submission" --file "./issues/final-submission.md"` will create an issue in all pgroups, with body content read from said file.

### `create-personal-repos`

create personal repos on gitea for all canvas students. You may specify an optional suffix.

Example: `python3 -m joint_teapot create-personal-repos --suffix "-p1"` will create repos named `StudentNameStudentID-p1`.

### `create-teams`

create teams on gitea by canvas groups

### `create-webhooks-for-mm`

Create a pair of webhooks on gitea and mm for all student groups on gitea, and configure them so that updates on gitea will be pushed to the mm channel. Optionally specify a prefix to ignore all repos whose names do not start with it.

Example: `python3 -m joint_teapot create-webhooks-for-mm p1` will fetch all repos whose names start with `"p1"` and create two-way webhooks for these repos. All repos should already have same-name mm channels. If not, use `create-channels-on-mm` to create them.

### `get-no-collaborator-repos`

list all repos with no collaborators

### `get-public-keys`

list all public keys on gitea

### `get-repos-status`

list status of all repos with conditions

### `invite-to-teams`

invite all canvas students to gitea teams by team name

### `prepare-assignment-dir`

prepare assignment dir from extracted canvas "Download Submissions" zip

### `unsubscribe-from-repos`

Unsubscribe from all repos in the organization specified in the config file where the repo name matches a given regex expression.

Example: `python3 -m joint_teapot unsubscribe-from-repos '\d{12}$'` will remove all repos whose names end with a student ID number from your gitea subscription list. Refer to the Python `re` module docs for more info about regex.

### `upload-assignment-grades`

upload assignment grades to canvas from grade file (GRADE.txt by default), read the first line as grade, the rest as comments

## License

MIT
