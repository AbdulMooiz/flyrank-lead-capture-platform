# Build Log

## 2026-09-26

### Initial repository assessment

- Confirmed the repository is already present on branch `main` with the expected GitHub remote configured.
- Confirmed the project is a FastAPI + SQLAlchemy + Alembic + Redis + RQ service intended for a multi-tenant lead capture widget platform.
- Confirmed the initial app structure had already been constructed before this session, including database models, API routes, middleware, worker, and deployment files.

### Verification step

- Installed the project dependencies from `requirements.txt`.
- Executed the repository’s current app-level regression tests and validated the baseline behavior.
- Added a focused automated suite in `tests/test_core.py` to prove the app currently works for the verified requirements.

### Result

- The app baseline is passing for the core auth, widget, tenant-isolation, config, submission, analytics, oversized-payload, and rate-limit checks captured in the regression suite.
- The repository now includes real evidence in `EVIDENCE.md` and project usage notes in `README.md`.

### Continued implementation and runtime verification

- Added an explicit RQ retry policy with three attempts and increasing intervals for notification jobs.
- Enabled the RQ scheduler in the worker so delayed retry intervals are executed in live runtime.
- Added regression coverage for queue retry configuration, geo-provider fallback, and graceful geo degradation.
- Added regression coverage ensuring the worker starts with scheduling enabled.
- Built and started the complete Docker Compose stack successfully.
- Verified API health, demo delivery, database and Redis health, Alembic startup, worker startup, and a live registration/widget/submission flow.
- Confirmed the worker completed the live notification job successfully.

### Known limitations

- Live failure-and-retry behavior was verified with a deliberate failure: three attempts were executed and the job persisted as `failed`.
- Broader security acceptance tests remain outside the current verified baseline.
