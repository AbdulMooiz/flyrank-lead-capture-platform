# Evidence

This file records only verified project behavior backed by real commands and outputs from this repository.

## 1) Repository state

Command:

```
git status --short --branch
git branch
git remote -v
git log -10 --oneline
```

Observed result:

- branch: `main`
- remote: `https://github.com/AbdulMooiz/flyrank-lead-capture-platform.git`
- last commits:
  - `5559bfd build architecture for running smoothly`
  - `dd9de2e chore: bootstrap capstone service foundation`

## 2) Docker Compose configuration validation

Command:

```
docker compose config --services
docker compose config
```

Observed result:

- services present: `db`, `redis`, `api`, `demo`, `worker`
- compose file resolves without syntax errors

## 3) Automated regression verification

Command:

```
cd /d C:\Users\17abd\flyrank-lead-capture-platform && python -m pytest tests/test_core.py -q
```

Observed result:

- `4 passed` in `30.06s`

Verified behaviors:

- registration and login work
- widget creation and tenant isolation work
- public widget config route works and responds with cache headers
- CORS preflight for `http://localhost:5500` succeeds
- oversized request payload is rejected with `413`
- rate limiting triggers once the configured threshold is exceeded
- dashboard analytics and submissions endpoint return expected data

## 4) Local runtime dependency check

Command:

```
python -m pip install -r requirements.txt
```

Observed result:

- dependencies installed successfully for the project runtime

## 5) Current status

The repository is ready to continue from the verified baseline, with evidence recorded for the behaviors above.
