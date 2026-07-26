# Cliniar

> Self-hosted, offline-first, agent-native work management with a
> Linear-compatible GraphQL interface.

Cliniar combines a type-safe CLI, an optional MCP server, and a generic
self-hosted backend. It is designed for humans, agents, and automation:
responses are validated Pydantic models, commands compose in shell pipelines,
and JSON output is the stable machine contract. Use the hosted Linear API or
point the same client at a local SQLite or shared PostgreSQL deployment.

```
cliniar me                          # who am I?
cliniar team list                   # all teams in workspace
cliniar issue list --assignee me    # my issues
cliniar issue create --team ENG --title "Fix login bug" --priority 1
cliniar -o json issue list | jq '.[].title'    # pipe into anything
```

---

## Why Cliniar?

- **Type-safe.** Every response validated through Pydantic v2. No silent schema drift.
- **Agent-first.** Stable JSON contracts; pipe-friendly `-o ids` / `-o md` / `-o yaml`.
- **Tiny attack surface.** Only Pydantic + httpx + Typer + Rich. No npm chaos, no `postinstall` hooks.
- **Honest errors.** Linear API errors surfaced verbatim with proper POSIX exit codes.
- **Offline-first and self-hostable.** Work locally without a network dependency
  or deploy the same generic backend with PostgreSQL.
- **Built for automation.** `--dry-run` for safe mutation previews, `raw query` escape hatch for any GraphQL.

---

## Install

```bash
# From PyPI (recommended)
pip install cliniar
# or
uv tool install cliniar
```

```bash
# From source
git clone <repository-url> cliniar
cd cliniar
uv venv && source .venv/bin/activate
uv pip install -e .
```

---

## Quick Start

### 1. Get a token

Generate a personal API key at <https://linear.app/settings/api>.

### 2. Set it up

```bash
export LINEAR_TOKEN="lin_api_..."
# Or persist a config:
cliniar init
```

### 3. Verify

```bash
cliniar me
```

### 4. Use it

```bash
# Read
cliniar team list
cliniar issue get ENG-123
cliniar issue list --assignee me --state Todo

# Write
cliniar issue create --team ENG --title "Fix login bug" --priority 1
cliniar issue assign ENG-123 me
cliniar issue state ENG-123 "In Progress"
cliniar issue prio ENG-123 1
cliniar comment add ENG-123 "Started on this — investigating now"

# Pipe
cliniar -o ids issue list --assignee me | xargs -I{} cliniar issue url {}
cliniar -o json issue list --state Todo | jq '.[] | "\(.identifier): \(.title)"'

# Safety net
cliniar --dry-run issue update ENG-123 --priority 2
```

---

## Output Formats

Set with `-o` / `--output` **before** the subcommand:

| Format | Flag | What you get |
|---|---|---|
| **human** | default | Pretty Rich tables with colors |
| **json** | `-o json` | Compact JSON, null-pruned |
| **yaml** | `-o yaml` | Hand-rolled minimal YAML |
| **md** | `-o md` | Markdown tables for PRs / reports |
| **plain** | `-o plain` | TSV — `id<TAB>state<TAB>...` |
| **ids** | `-o ids` | Just identifiers, one per line — great for `xargs` |

---

## Command Reference

```
cliniar
├── me / auth status / auth whoami
├── init                          Create ~/.config/cliniar/config.toml
├── team list / get / states / members
├── issue
│   ├── list   --team --state --assignee --label --priority --contains ...
│   ├── get <id>
│   ├── create --team --title [--description --priority --assignee --label ...]
│   ├── update <id> [--title --state --assignee --priority --label ...]
│   ├── state <id> <state-name>
│   ├── assign <id> <user>
│   ├── prio <id> <0-4>
│   ├── url <id>
│   └── search <query>
├── project list / get
├── cycle current <team> / list <team>
├── comment list / add / edit / delete
├── label list / create / delete
└── raw query <graphql>           Escape hatch — arbitrary GraphQL
```

Run `cliniar <command> --help` for full flags on any subcommand.

---

## Configuration

Default location: `~/.config/cliniar/config.toml`. Override with `$CLINIAR_CONFIG`.

```toml
[auth]
token_env = "LINEAR_TOKEN"  # read from this env var

[defaults]
team = "ENG"
output = "human"

[display]
color = true
table_max_width = 120
```

Run `cliniar init` to scaffold the file.

### Migration from `clinear` (v0.7.0)

The `clinear`, `clinear-mcp`, and `clinear-serve` executable aliases are
deprecated but remain available for one release. New integrations must use
`cliniar`, `cliniar-mcp`, and `cliniar-serve`.

Cliniar reads `CLINIAR_*` variables and the canonical
`~/.config/cliniar/config.toml` and `$XDG_DATA_HOME/cliniar/` locations first.
For the same one-release transition it falls back to matching `CLINEAR_*`
variables and legacy `~/.config/clinear/` and `$XDG_DATA_HOME/clinear/` paths
when no canonical value exists. `LINEAR_TOKEN`, `LINEAR_API_URL`, Linear API
field names, and GraphQL wire names are unchanged. Migrate files rather than
maintaining two writable copies:

```bash
mkdir -p ~/.config/cliniar
cp ~/.config/clinear/config.toml ~/.config/cliniar/config.toml
```

### Self-hosted backend

Install `cliniar[server]` to run the Linear-compatible backend with either
isolated SQLite files or a shared PostgreSQL database:

```bash
pip install 'cliniar[server]'
cliniar-serve seed --tenant local
cliniar-serve serve --tenant local
```

Point an account's `base_url` (or `LINEAR_API_URL`) at the resulting
`/graphql` endpoint. `CLINIAR_DATABASE_URL` selects shared PostgreSQL storage,
while `CLINIAR_APP_URL` controls the browser-facing issue and project links
returned by the backend. See [the deployment guide](docs/DEPLOYMENT.md) for
database precedence, multi-organization token provisioning, and health checks.

---

## Exit Codes (stable across versions)

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Generic error |
| 2 | Usage error (bad flags) |
| 3 | Auth error (missing/invalid token) |
| 4 | Not found |
| 5 | Validation error (response didn't match model) |
| 6 | API error (Linear returned errors) |
| 7 | Network error (timeout, DNS, TLS) |
| 8 | Rate limited |

---

## Security

- Token read from `$LINEAR_TOKEN`, `--token` flag, or `config.toml`. Never logged in plaintext.
- HTTPS-only. TLS verification mandatory.
- No telemetry. Outbound API calls go only to the configured account endpoint
  (`api.linear.app` by default, or an explicitly configured compatible backend).
- Pre-commit hook blocks committing tokens, `.log` files, `.env` files. See `scripts/pre-commit.sh`.

---

## Development

See [AGENTS.md](./AGENTS.md) for the contributor guide — architecture, testing, version bumping, and release process.

```bash
git clone <repository-url> cliniar
cd cliniar
bash scripts/install-hooks.sh    # install pre-commit hook
uv venv && uv pip install -e ".[dev]"
export LINEAR_TOKEN="lin_api_..."
bash scripts/e2e-test.sh         # 36/36 should pass
```

---

## License

MIT — see [LICENSE](./LICENSE).

---

## For AI agents — Skill & MCP server

cliniar ships with two artifacts specifically for AI coding agents:

### 1. Agent skill bundle

A Swarm/Claude-style skill that teaches an agent both the mechanics of
`cliniar` and the *behavior* of working through Linear (search before
create, use `--output json` for pipes, chain commands in shell instead of
writing Python, etc.).

Install:

```bash
git clone <repository-url> cliniar
cd cliniar
bash skills/install.sh
```

This symlinks `skills/cliniar/` into BOTH:

- `~/.swarmos/skills/cliniar/` (for Swarm OS)
- `~/.claude/skills/cliniar/` (for Claude Code / Claude Desktop)

Flags: `--swarm-only`, `--claude-only`, `--copy` (no symlinks), `--uninstall`.

### 2. MCP server (`cliniar-mcp`)

An optional Model Context Protocol server that exposes the same teaching
content as an MCP tool, plus read-only Linear resources and prompt
templates for common workflows.

**What it exposes:**

- **1 tool** — `cliniar_guide(topic)` returns structured teaching content.
  Topics: `overview`, `commands`, `workflows`, `filters`, `output-formats`,
  `examples`.
- **7 read-only resources** — `cliniar://me`, `cliniar://issue/{id}`,
  `cliniar://team/{key}`, `cliniar://project/{id_or_slug}`,
  `cliniar://cycle/current/{team_key}`, `cliniar://issues/mine`,
  `cliniar://issues/team/{team_key}`.
- **6 prompts** — `triage`, `daily_standup`, `create_from_error`,
  `hand_off`, `cycle_review`, `issue_investigate`.

**The server exposes NO mutation tools** by design. Mutations are performed
via the `cliniar` CLI through the agent's Bash tool — the MCP tool's
response and every prompt body include a behavioral reminder reinforcing
this rule.

#### Step 1 — Install

The server is an optional extra. Pick one:

```bash
# Option A — pip
pip install 'cliniar[mcp]'

# Option B — uv (recommended; isolated tool install)
uv tool install --with mcp 'cliniar==0.3.0'

# Option C — pipx
pipx install 'cliniar[mcp]'
```

After install, you should have **both** binaries on `PATH`:

```bash
which cliniar           # /home/you/.local/bin/cliniar
which cliniar-mcp       # /home/you/.local/bin/cliniar-mcp
cliniar --version       # cliniar 0.3.0
```

#### Step 2 — Set up the Linear token

The MCP server reads the same token as the CLI. Pick one:

```bash
# Option A — env var (simplest; works for all clients)
export LINEAR_TOKEN="<YOUR_LINEAR_TOKEN>"
# Persist it in your shell rc:
echo 'export LINEAR_TOKEN="<YOUR_LINEAR_TOKEN>"' >> ~/.bashrc
# Or ~/.zshrc, ~/.config/fish/config.fish, etc.

# Option B — config file (good for desktop apps that don't inherit shell env)
cliniar init                          # writes ~/.config/cliniar/config.toml
# Then edit ~/.config/cliniar/config.toml:
#   [auth]
#   token = "<YOUR_LINEAR_TOKEN>"
```

Get your token at <https://linear.app/settings/api> (create a personal API
key). Verify it works:

```bash
cliniar me            # should print your Linear profile
cliniar auth status   # shows which token source resolved
```

> **Note for desktop MCP clients** (Claude Desktop, Cursor, etc.): GUI
> apps usually do **not** inherit your shell's `export`s. Either put the
> token in the config file (Option B) **or** pass it via the MCP server
> entry's `env` block (shown below for each client).

#### Step 3 — Register with your MCP client

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "cliniar": {
      "command": "cliniar-mcp",
      "env": {
        "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>"
      }
    }
  }
}
```

**Claude Code (CLI)** — add via the `claude mcp` command:

```bash
claude mcp add cliniar cliniar-mcp --env LINEAR_TOKEN=<YOUR_LINEAR_TOKEN>
```

Or edit `~/.claude.json` directly:

```json
{
  "mcpServers": {
    "cliniar": {
      "command": "cliniar-mcp",
      "env": { "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>" }
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "cliniar": {
      "command": "cliniar-mcp",
      "env": { "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>" }
    }
  }
}
```

**Swarm OS** — drop the same config into your Swarm MCP config
(`~/.swarmos/mcp/servers.json` or via `swarm mcp add`):

```bash
swarm mcp add cliniar --command cliniar-mcp --env LINEAR_TOKEN=<YOUR_LINEAR_TOKEN>
```

**Codex CLI** (`~/.config/codex/mcp.json`):

```json
{
  "servers": {
    "cliniar": {
      "command": "cliniar-mcp",
      "env": { "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>" }
    }
  }
}
```

If `cliniar-mcp` is not on the system `PATH` of the GUI app (common on macOS),
use the absolute path:

```json
{
  "mcpServers": {
    "cliniar": {
      "command": "/home/you/.local/bin/cliniar-mcp",
      "env": { "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>" }
    }
  }
}
```

Find the absolute path with `which cliniar-mcp`.

#### Step 4 — Verify the wiring

Restart the MCP client and confirm the server connects. From inside the
client you should see:

- **1 tool**: `cliniar_guide`
- **2 concrete resources**: `cliniar://me`, `cliniar://issues/mine`
- **5 resource templates**: `cliniar://issue/{id}`, `cliniar://team/{key}`,
  `cliniar://project/{id_or_slug}`, `cliniar://cycle/current/{team_key}`,
  `cliniar://issues/team/{team_key}`
- **6 prompts**: `triage`, `daily_standup`, `create_from_error`,
  `hand_off`, `cycle_review`, `issue_investigate`

If you have the MCP Inspector installed, you can also smoke-test from a
terminal:

```bash
npx @modelcontextprotocol/inspector cliniar-mcp
```

This launches a browser UI that lets you list tools/resources/prompts and
invoke them interactively.

For a quick stdio sanity check without the Inspector:

```bash
(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
 echo '{"jsonrpc":"2.0","method":"notifications/initialized"}'
 echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}') | cliniar-mcp | head -3
```

You should see a JSON-RPC initialize response followed by `tools/list`
returning `cliniar_guide`.

#### Troubleshooting

| Symptom | Fix |
|---|---|
| `cliniar-mcp: command not found` in GUI app | Use absolute path in the MCP config (`which cliniar-mcp`) |
| Server starts but resource reads return auth error | Token not visible to the server — pass it via the config's `env` block instead of relying on shell `export` |
| `pip install 'cliniar[mcp]'` fails with quoting error | Some shells eat the brackets — quote the whole spec or escape: `pip install cliniar\[mcp\]` |
| Tool list is empty in client | Restart the MCP client after editing the config; some clients cache `tools/list` |
| Stdout looks corrupted | Don't run `cliniar-mcp` interactively — it speaks JSON-RPC on stdin/stdout. Logs go to stderr. |
