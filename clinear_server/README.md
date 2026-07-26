# clinear_server — local Linear-compatible backend

A self-hosted GraphQL server that speaks the exact subset of the Linear API the
`clinear` CLI uses. Run `clinear` **fully offline** against a single-file SQLite
database, **multi-tenant**, with **no rate limits**.

> The CLI needs only one change to talk to it: an `accounts.<name>.base_url`
> pointing at this server. Everything else is byte-for-byte identical.

## Install

```bash
pip install 'clinear[server]'      # adds ariadne, fastapi, uvicorn, sqlalchemy, aiosqlite
```

## Quick start (offline, 60 seconds)

```bash
# 1. Seed a tenant DB (org, admin user, team ENG, workflow states, token)
clinear-serve seed --tenant default
#   -> prints:  TOKEN : lin_api_XXXXXXXX...

# 2. Start the server
clinear-serve serve --tenant default --port 8787
#   -> http://127.0.0.1:8787/graphql

# 3. Point clinear at it  (~/.config/clinear/config.toml)
cat >> ~/.config/clinear/config.toml <<'TOML'
[accounts.local]
base_url = "http://127.0.0.1:8787/graphql"
token = "lin_api_XXXXXXXX..."      # the token printed by `seed`
TOML

# 4. Use clinear normally
clinear --account local me
clinear --account local issue create --team ENG --title "Hello local"
clinear --account local issue list
```

`$LINEAR_API_URL` overrides `base_url` for any account, e.g.:

```bash
LINEAR_API_URL=http://127.0.0.1:8787/graphql clinear me
```

## Commands

| Command | Purpose |
|---------|---------|
| `clinear-serve seed`  | Provision a tenant DB (org/user/team/states/token). Prints the token. |
| `clinear-serve serve` | Run the GraphQL server (`--host`, `--port`, `--open`, `--db`, `--tenant`). |
| `clinear-serve token` | Mint an additional API token for a tenant. |

`--open` (offline convenience): any token maps to the first seeded identity — no
token management needed for single-user local dev.

## What it implements

**Queries:** `viewer`, `teams`, `team` (+ `states`/`members`/`cycles`/`activeCycle`),
`issues` (with `IssueFilter` + `orderBy`), `issue` (+ `comments`/`labels`/`subscribers`),
`projects`, `project`, `issueLabels`, `searchIssues`, `rateLimitStatus`.

**Mutations:** `issueCreate/Update/Delete/Archive`, `commentCreate/Update/Delete`,
`issueLabelCreate/Delete`, `projectCreate/Update/Archive`.

**Semantics:** per-team incrementing identifiers (`ENG-1`, `ENG-2`, …), seeded
workflow states (Backlog/Todo/In Progress/In Review/Done/Canceled), derived
`priorityLabel`/`url`/`branchName`, state-transition timestamps
(`startedAt`/`completedAt`/`canceledAt`), soft-delete via `archivedAt`, and the
Relay `{ nodes, pageInfo }` connection envelope.

## Multi-tenancy

Each API token maps to exactly one organization. Every resolver is scoped by
`organization_id`, so tenants cannot see each other's data. One server endpoint
serves many tenants — add several `accounts.<name>` in clinear config, all with
the same `base_url` but different tokens.

## No rate limits

The server never returns HTTP 429 and implements `rateLimitStatus` with
effectively-unlimited values, so any client polling it is satisfied.

## Storage

Offline: one SQLite file per tenant at
`$XDG_DATA_HOME/clinear/<tenant>.db` (default `~/.local/share/clinear/`), WAL mode.
The schema carries `organization_id` on every table, so the same resolvers work
against a shared Postgres database for a hosted/SaaS deployment (latent seam).

## Architecture

```
clinear_server/
├── schema.graphql   SDL — exact Linear camelCase field names
├── db.py            SQLAlchemy Core tables, engine, migrate, seed
├── store.py         org-scoped reads + serializers + filter compilers
├── writer.py        mutations (identifier counter, derived fields)
├── resolvers.py     Ariadne bindings (Relay envelope, lazy field resolvers)
├── app.py           Starlette app + token-auth middleware + /graphql + /health
└── cli.py           `clinear-serve` entry point (serve|seed|token)
```

## Prove it

```bash
bash scripts/e2e-local-backend.sh      # 17/17 checks: boots server + drives real clinear CLI
```
