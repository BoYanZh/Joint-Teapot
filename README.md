# Joint Teapot

A handy tool for TAs in JI to handle stuffs through [Gitea](https://focs.ji.sjtu.edu.cn/git/), [Canvas](https://umjicanvas.com/), and [JOJ](https://joj.sjtu.edu.cn/). Joint is related to JI and also this tool which join websites together. Teapot means to hold Gitea, inspired by [@nichujie](https://github.com/nichujie).

## Getting Started

### Setup venv (Optional)

```bash
python3 -m venv env
source env/Scripts/activate
```

### Install

```bash
pip3 install -e .
vi .env # configure environment
```

### For developers

```bash
pip3 install -r requirements-dev.txt
pre-commit install
pytest -svv
```
