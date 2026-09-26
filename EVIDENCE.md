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
- last commit: `3c1d1b5 RQ retry policy: 3 attempts with intervals [1, 5, 15] Geo-provider fallback and graceful degradation tests Updated EVIDENCE.md and BUILDLOG.md Verified full Docker Compose runtime Verified live registration → widget creation → submission → worker processing`
- branch state: clean and synchronized with `origin/main` at the last checkpoint

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

- `7 passed` in `34.69s`

Verified behaviors:

- registration and login work
- widget creation and tenant isolation work
- public widget config route works and responds with cache headers
- CORS preflight for `http://localhost:5500` succeeds
- oversized request payload is rejected with `413`
- rate limiting triggers once the configured threshold is exceeded
- dashboard analytics and submissions endpoint return expected data
- notification enqueue uses an RQ retry policy with three attempts
- the worker starts with the RQ scheduler enabled for delayed retries
- geo enrichment falls back from `ip-api.com` to `ipapi.co`
- geo enrichment returns an empty result when both providers fail

## 4) Local runtime dependency check

Command:

```
python -m pip install -r requirements.txt
```

Observed result:

- dependencies installed successfully for the project runtime

## 5) Docker runtime smoke test

Commands:

```
docker compose up -d --build
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:5500
docker compose ps
docker compose logs --no-color --tail=30 api worker
```

Observed result:

- API health returned `200` with `{"status":"ok"}`
- demo server returned `200`
- PostgreSQL and Redis reported healthy
- Alembic migration completed and the API started successfully
- worker started and listened on the `notifications` queue
- live registration returned `201`, widget creation succeeded, and a public submission returned `status=received`
- worker logged successful completion of `app.workers.worker.process_notification`
- a deliberate failure was retried three times and persisted as `status=failed`, `attempts=3`

## 6) Current status

The repository is ready for the next commit and push, with automated and live Docker evidence recorded for the behaviors above.
