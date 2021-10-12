# Joint Teapot

A handy tool for TAs in JI to handle works through [Gitea](https://focs.ji.sjtu.edu.cn/git/), [Canvas](https://umjicanvas.com/), and [JOJ](https://joj.sjtu.edu.cn/). Joint is related to JI and also this tool which join websites together. Teapot means to hold Gitea, inspired by [@nichujie](https://github.com/nichujie).

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
