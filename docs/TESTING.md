# Testing m3utolocal

## Local (Linux)

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q
```

## FreeBSD host (app-test-001)

```bash
# packages
sudo pkg install -y py312-requests py312-pytest py312-pytest-cov py312-responses

# sync & run
rsync -avz --delete --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
  -e ssh ./ mlapointe@172.16.176.133:~/src/m3utolocal/
ssh mlapointe@172.16.176.133 'cd ~/src/m3utolocal && python3.12 -m pytest -q'
```

## Layout

- `tests/unit/` — pure logic, HTTP mocks
- `tests/integration/` — pipelines
- `tests/ui/` — Textual Pilot (later)
- `tests/fixtures/` — sample M3U files

## Rules

- No real network in unit tests
- Downloads must never write finished media to CWD
- Prefer TDD: red → green → refactor
