# Joint Teapot

## Installation

### Setup venv (Optional)

```bash
python3 -m venv env
source env/Scripts/activate
```

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
