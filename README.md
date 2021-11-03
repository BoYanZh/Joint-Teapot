# Joint Teapot

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/352635b2c8534b0086b5a153db7c82e9)](https://app.codacy.com/gh/BoYanZh/Joint-Teapot?utm_source=github.com&utm_medium=referral&utm_content=BoYanZh/Joint-Teapot&utm_campaign=Badge_Grade_Settings)

A handy tool for TAs in JI to handle works through [Gitea](https://focs.ji.sjtu.edu.cn/git/), [Canvas](https://umjicanvas.com/), and [JOJ](https://joj.sjtu.edu.cn/). Joint is related to JI and also this tool which join websites together. Teapot means to hold Gitea, inspired by [@nichujie](https://github.com/nichujie).

This tool is still under heavy development. The docs may not be updated on time, and all the features are provided with the probability to change.

## Getting Started

### Setup venv (Optional)

```bash
python3 -m venv env # you only need to do that once
source env/Scripts/activate # each time when you need this venv
```

### Install

```bash
pip3 install -e .
cp .env.exmaple .env && vi .env # configure environment
joint-teapot --help
```

### For developers

```bash
pip3 install -r requirements-dev.txt
pre-commit install
pytest -svv
```

## Features

- [x] retrieve the hw/project releases for all students
- [x] open "bulk issues" to report something wrong
- [x] collect all the public keys
- [x] import groups (create teams)
- [x] create repos
- [x] archive all repos of a course
- [x] check whether an issue exists with appointed title

## License

MIT
