# Self-hosted backend deployment

`clinear_server` is a Linear-compatible GraphQL backend for `clinear`. It can
use an isolated SQLite file for local work or a shared PostgreSQL database for
multiple organizations. The backend is generic: organization names, URL keys,
users, teams, application URLs, and database targets are deployment inputs.

## Install

```bash
python -m pip install 'clinear[server]'
```

The server extra includes Ariadne, Starlette/FastAPI, Uvicorn, SQLAlchemy,
SQLite support, and the psycopg 3 binary PostgreSQL driver.

## Database target resolution

`serve`, `seed`, `token`, and programmatic `create_app` use one precedence rule:

1. explicit `--database-url`;
2. `CLINEAR_DATABASE_URL`;
3. the existing `--db` path, or the SQLite path derived from `--tenant`.

`--database-url` accepts a SQLAlchemy URL such as
`postgresql+psycopg://USER:PASSWORD@DB_HOST:5432/DATABASE`. Do not place
credentials in source control or command logs; prefer a secret-injected
`CLINEAR_DATABASE_URL`. CLI status output redacts URL passwords.

SQLite retains WAL mode and foreign-key pragmas. PostgreSQL does not receive
SQLite pragmas and enables `pool_pre_ping` so stale pooled connections are
discarded before use.

## Isolated SQLite

```bash
clinear-serve seed \
  --tenant local \
  --org "Local Workspace" \
  --org-key local \
  --team-key ENG \
  --email user@example.test

clinear-serve serve --tenant local --host 127.0.0.1 --port 8787
```

Without `--db`, the file is
`$XDG_DATA_HOME/clinear/<tenant>.db` or
`~/.local/share/clinear/<tenant>.db`.

`--open` is intended only for isolated local use. It resolves an identity only
when the SQLite database contains exactly one organization and one user. It is
disabled by ambiguity and never selects the first global user in PostgreSQL.

## Shared PostgreSQL

Create a dedicated database and role using your normal PostgreSQL provisioning
tooling, then inject its URL:

```bash
export CLINEAR_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@DB_HOST:5432/DATABASE'
export CLINEAR_APP_URL='https://issues.example.com'

clinear-serve migrate

clinear-serve seed \
  --org "Engineering" \
  --org-key engineering \
  --team-key ENG \
  --user "Initial Admin" \
  --email admin@example.com

clinear-serve seed \
  --org "Operations" \
  --org-key operations \
  --team-key OPS \
  --user "Operations Admin" \
  --email ops-admin@example.com

clinear-serve serve --host 0.0.0.0 --port 8787
```

Each organization must have a unique `--org-key`. Seeding rejects duplicates
with a clear error and does not contain deployment-specific defaults or modes.

In a shared database, minting a token requires an explicit organization plus
one user selector:

```bash
clinear-serve token \
  --organization engineering \
  --email admin@example.com \
  --label automation

# User IDs are also accepted:
clinear-serve token \
  --organization engineering \
  --user USER_ID \
  --label service
```

The organization selector accepts an organization ID or URL key. The user must
belong to that organization; token creation never falls back to a user from a
different organization.

## Application and API URLs

`CLINEAR_APP_URL` is the browser-facing base used for generated issue and
project URLs. Its sensible local default is `http://localhost:8787`. Set it to
the public owned application origin in hosted environments; generated URLs do
not require `linear.app`.

The GraphQL API remains at `/graphql`. Point each client account at it:

```toml
[accounts.hosted]
base_url = "https://api.example.com/graphql"
token = "TOKEN_FROM_A_SECRET_STORE"
```

`LINEAR_API_URL` can override the client-side account URL. It is separate from
`CLINEAR_APP_URL`.

## Health, readiness, and operation

- `GET /health` is a process liveness endpoint and returns HTTP 200 without
  requiring a database round trip.
- `GET /ready` verifies database connectivity and the applied schema revision.
  It returns HTTP 200 with `{"status":"ready"}`, or HTTP 503 when the database
  is unavailable or its schema is behind the server.

Use `/health` for process supervision and `/ready` for load-balancer or
orchestrator readiness. Terminate TLS at a trusted reverse proxy, inject
database credentials through a secret manager, restrict database network
access, back up PostgreSQL normally, and monitor readiness failures.

Schema changes are ordered and recorded in `schema_revision`. Run
`clinear-serve migrate` as a pre-deployment or init step before starting new
application instances. The server process does not alter schema on startup, so
`/health` remains available during a database outage and `/ready` rejects
traffic until both connectivity and schema currency are confirmed.

## Verification

SQLite requires no external service:

```bash
uv run --extra server --extra dev python -m pytest -q \
  tests/test_server_backend.py tests/test_server_postgres.py
bash scripts/e2e-local-backend.sh
```

PostgreSQL integration tests are opt-in and never start Docker:

```bash
export CLINEAR_TEST_POSTGRES_URL='postgresql+psycopg://USER:PASSWORD@DB_HOST:5432/TEST_DATABASE'
uv run --extra server --extra dev python -m pytest -q tests/test_server_postgres.py

# Run the same 17-check CLI matrix against PostgreSQL:
CLINEAR_DATABASE_URL="$CLINEAR_TEST_POSTGRES_URL" \
CLINEAR_PYTHON="$PWD/.venv/bin/python" \
bash scripts/e2e-local-backend.sh
```

Use a disposable test database. The gated test creates uniquely named
organizations and removes its rows afterward.
