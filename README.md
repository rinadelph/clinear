# Hoja

**A self-hosted workspace for issues, projects, cycles, and team work.** Hoja includes a browser UI and a Python CLI. It can run against its own SQLite or PostgreSQL-backed service; the GraphQL API also implements a Linear-compatible surface for clients that use it.

The Python distribution and commands are named **Cliniar**: `cliniar`, `cliniar-serve`, and the optional `cliniar-mcp`.

## What you can do

- Sign in to a workspace, switch between memberships, and create workspaces, teams, and members.
- Create, search, filter, assign, and update issues; browse team boards and cycles; open issue details and comment.
- Organize projects, review project issues and updates, and manage initiatives.
- Use Inbox for future issue notifications, with unread/read and archive controls. Existing historical events are not backfilled.
- Save issue and project views in the browser. These views are local to that browser, not shared workspace records.
- Use the CLI for shell workflows and automation. Responses are validated models; `--output json` and `--output ids` are suitable for scripts.

Hoja does not require Linear Cloud. The API uses Linear-compatible GraphQL names and accepts `LINEAR_TOKEN` and `LINEAR_API_URL` so compatible clients can target a Hoja server. Compatibility does not mean every Linear feature is implemented. Unsupported screens or controls are presented as unavailable rather than simulated as working.

## Run the workspace

Docker Compose starts the app and PostgreSQL:

```bash
docker compose up --build -d
docker compose exec app cliniar-serve seed \
  --org "Example Workspace" \
  --org-key example \
  --team-key ENG \
  --user "Workspace Admin" \
  --email admin@example.com
```

Open [http://localhost:8787](http://localhost:8787) and sign in with the token printed by `seed`. Set `POSTGRES_PASSWORD` before using Compose beyond local development. See [deployment](docs/DEPLOYMENT.md) for database setup, migrations, readiness checks, and multi-organization token provisioning.

For an isolated SQLite instance instead:

```bash
python -m pip install 'cliniar[server]'
cliniar-serve seed --tenant local --org "Local Workspace" \
  --org-key local --team-key ENG --email user@example.test
cliniar-serve serve --tenant local --host 127.0.0.1 --port 8787
```

## Use the CLI

Install the CLI from PyPI or from a checkout:

```bash
python -m pip install cliniar
# or, from this repository:
uv sync --extra dev --extra server
```

Configure an account in `~/.config/cliniar/config.toml`:

```toml
[accounts.local]
base_url = "http://127.0.0.1:8787/graphql"
token_env = "LINEAR_TOKEN"

[defaults]
default_account = "local"
```

Export the token as `LINEAR_TOKEN` (or choose a different `token_env` for the
account), then try:

```bash
cliniar me
cliniar team list
cliniar issue list --assignee me
cliniar issue create --team ENG --title "Review onboarding flow"
cliniar -o json issue list --state Todo
```

The CLI also supports projects, cycles, comments, labels, raw GraphQL queries, and dry-run previews for supported mutations. Run `cliniar --help` or `cliniar <command> --help` for the current command and option list. For compatibility with existing Linear accounts, `LINEAR_TOKEN` and `LINEAR_API_URL` remain supported.

## Agent integrations

The optional MCP server provides one guide tool, seven read-only resources, and six workflow prompts. It does not expose mutation tools; make changes through the CLI.

```bash
python -m pip install 'cliniar[mcp]'
```

Register `cliniar-mcp` as a stdio MCP server in your client, passing the needed token through that client's environment configuration. The server reads the same account configuration as the CLI. See [the MCP section below](#mcp-server-setup) for a complete example.

The repository also includes an installable agent skill:

```bash
bash skills/install.sh --claude-only
```

It installs the `skills/cliniar` instructions into the selected agent skill directory; `--copy` copies rather than symlinks.

## MCP server setup

Install the optional MCP dependency alongside the CLI:

```bash
python -m pip install 'cliniar[mcp]'
```

For Claude Desktop, add a server entry to its MCP configuration. Use an absolute
executable path if the GUI does not inherit your shell `PATH`:

```json
{
  "mcpServers": {
    "cliniar": {
      "command": "/absolute/path/to/cliniar-mcp",
      "env": {
        "LINEAR_TOKEN": "<workspace-token>"
      }
    }
  }
}
```

Replace the command path with the result of `which cliniar-mcp`. If the selected
account sets a custom `token_env`, pass that variable instead. The MCP server
provides one guide tool, seven read-only resources, and six workflow prompts;
it does not provide mutation tools.

## Development

Python 3.10 or newer is required. Install development and backend dependencies, then run the tests:

```bash
uv sync --extra dev --extra server
uv run pytest
```

Build the browser app with `npm ci && npm run build` in `frontend/`. The local backend integration script is `bash scripts/e2e-local-backend.sh`; it uses a disposable local database. The live API CLI matrix in `scripts/e2e-test.sh` requires `LINEAR_TOKEN`, `CLINIAR_TEST_TEAM`, and `CLINIAR_TEST_ISSUE`.

Product architecture is described in [Design](docs/DESIGN.md); deployment instructions are in [Deployment](docs/DEPLOYMENT.md). The [changelog](CHANGELOG.md) records release-level behavior changes.
