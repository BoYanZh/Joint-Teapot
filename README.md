# Joint Teapot

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/352635b2c8534b0086b5a153db7c82e9)](https://app.codacy.com/gh/BoYanZh/Joint-Teapot?utm_source=github.com&utm_medium=referral&utm_content=BoYanZh/Joint-Teapot&utm_campaign=Badge_Grade_Settings)

A handy tool for TAs in JI to handle works through [Gitea](https://focs.ji.sjtu.edu.cn/git/), [Canvas](https://umjicanvas.com/), and [JOJ](https://joj.sjtu.edu.cn/). Joint is related to JI and also this tool which join websites together. Teapot means to hold Gitea, inspired by [@nichujie](https://github.com/nichujie).

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
create channels for student groups according to group information on gitea. Optionally specify a prefix to ignore all repos whose names do not start with it.
### `create-issues`
create issues on gitea
### `create-personal-repos`
create personal repos on gitea for all canvas students
### `create-teams`
create teams on gitea by canvas groups
### `create-webhooks-for-mm`
Create a pair of webhooks on gitea and mm for all student groups on gitea, and configure them so that updates on gitea will be pushed to the mm channel. Optionally specify a prefix to ignore all repos whose names do not start with it.
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
### `upload-assignment-grades`
upload assignment grades to canvas from grade file (GRADE.txt by default), read the first line as grade, the rest as comments

## License

MIT
