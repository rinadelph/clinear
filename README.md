# clinear

> Type-safe Linear CLI built on Pydantic v2 + httpx + Typer.

A Linear command-line interface designed for **humans, agents, and CI/CD pipelines**. Every API response is a validated Pydantic model. Every command works in shell pipelines. JSON output is the canonical contract; the pretty human tables sit on top of it.

```
clinear me                          # who am I?
clinear team list                   # all teams in workspace
clinear issue list --assignee me    # my issues
clinear issue create --team ENG --title "Fix login bug" --priority 1
clinear -o json issue list | jq '.[].title'    # pipe into anything
```

---

## Why clinear?

- **Type-safe.** Every response validated through Pydantic v2. No silent schema drift.
- **Agent-first.** Stable JSON contracts; pipe-friendly `-o ids` / `-o md` / `-o yaml`.
- **Tiny attack surface.** Only Pydantic + httpx + Typer + Rich. No npm chaos, no `postinstall` hooks.
- **Honest errors.** Linear API errors surfaced verbatim with proper POSIX exit codes.
- **Built for automation.** `--dry-run` for safe mutation previews, `raw query` escape hatch for any GraphQL.

---

## Install

```bash
# From PyPI (recommended)
pip install clinear
# or
uv tool install clinear
```

```bash
# From source
git clone https://github.com/rinadelph/clinear.git
cd clinear
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
clinear init
```

### 3. Verify

```bash
clinear me
```

### 4. Use it

```bash
# Read
clinear team list
clinear issue get ENG-123
clinear issue list --assignee me --state Todo

# Write
clinear issue create --team ENG --title "Fix login bug" --priority 1
clinear issue assign ENG-123 me
clinear issue state ENG-123 "In Progress"
clinear issue prio ENG-123 1
clinear comment add ENG-123 "Started on this — investigating now"

# Pipe
clinear -o ids issue list --assignee me | xargs -I{} clinear issue url {}
clinear -o json issue list --state Todo | jq '.[] | "\(.identifier): \(.title)"'

# Safety net
clinear --dry-run issue update ENG-123 --priority 2
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
clinear
├── me / auth status / auth whoami
├── init                          Create ~/.config/clinear/config.toml
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

Run `clinear <command> --help` for full flags on any subcommand.

---

## Configuration

Default location: `~/.config/clinear/config.toml`. Override with `$CLINEAR_CONFIG`.

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

Run `clinear init` to scaffold the file.

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
- No telemetry. Zero outbound calls except to `api.linear.app`.
- Pre-commit hook blocks committing tokens, `.log` files, `.env` files. See `scripts/pre-commit.sh`.

---

## Development

See [AGENTS.md](./AGENTS.md) for the contributor guide — architecture, testing, version bumping, and release process.

```bash
git clone https://github.com/rinadelph/clinear.git
cd clinear
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

clinear ships with two artifacts specifically for AI coding agents:

### 1. Agent skill bundle

A Swarm/Claude-style skill that teaches an agent both the mechanics of
`clinear` and the *behavior* of working through Linear (search before
create, use `--output json` for pipes, chain commands in shell instead of
writing Python, etc.).

Install:

```bash
git clone https://github.com/rinadelph/clinear.git
cd clinear
bash skills/install.sh
```

This symlinks `skills/clinear/` into BOTH:

- `~/.swarmos/skills/clinear/` (for Swarm OS)
- `~/.claude/skills/clinear/` (for Claude Code / Claude Desktop)

Flags: `--swarm-only`, `--claude-only`, `--copy` (no symlinks), `--uninstall`.

### 2. MCP server (`clinear-mcp`)

An optional Model Context Protocol server that exposes the same teaching
content as an MCP tool, plus read-only Linear resources and prompt
templates for common workflows.

**What it exposes:**

- **1 tool** — `clinear_guide(topic)` returns structured teaching content.
  Topics: `overview`, `commands`, `workflows`, `filters`, `output-formats`,
  `examples`.
- **7 read-only resources** — `clinear://me`, `clinear://issue/{id}`,
  `clinear://team/{key}`, `clinear://project/{id_or_slug}`,
  `clinear://cycle/current/{team_key}`, `clinear://issues/mine`,
  `clinear://issues/team/{team_key}`.
- **6 prompts** — `triage`, `daily_standup`, `create_from_error`,
  `hand_off`, `cycle_review`, `issue_investigate`.

**The server exposes NO mutation tools** by design. Mutations are performed
via the `clinear` CLI through the agent's Bash tool — the MCP tool's
response and every prompt body include a behavioral reminder reinforcing
this rule.

#### Step 1 — Install

The server is an optional extra. Pick one:

```bash
# Option A — pip
pip install 'clinear[mcp]'

# Option B — uv (recommended; isolated tool install)
uv tool install --with mcp 'clinear==0.3.0'

# Option C — pipx
pipx install 'clinear[mcp]'
```

After install, you should have **both** binaries on `PATH`:

```bash
which clinear           # /home/you/.local/bin/clinear
which clinear-mcp       # /home/you/.local/bin/clinear-mcp
clinear --version       # clinear 0.3.0
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
clinear init                          # writes ~/.config/clinear/config.toml
# Then edit ~/.config/clinear/config.toml:
#   [auth]
#   token = "<YOUR_LINEAR_TOKEN>"
```

Get your token at <https://linear.app/settings/api> (create a personal API
key). Verify it works:

```bash
clinear me            # should print your Linear profile
clinear auth status   # shows which token source resolved
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
    "clinear": {
      "command": "clinear-mcp",
      "env": {
        "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>"
      }
    }
  }
}
```

**Claude Code (CLI)** — add via the `claude mcp` command:

```bash
claude mcp add clinear clinear-mcp --env LINEAR_TOKEN=<YOUR_LINEAR_TOKEN>
```

Or edit `~/.claude.json` directly:

```json
{
  "mcpServers": {
    "clinear": {
      "command": "clinear-mcp",
      "env": { "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>" }
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "clinear": {
      "command": "clinear-mcp",
      "env": { "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>" }
    }
  }
}
```

**Swarm OS** — drop the same config into your Swarm MCP config
(`~/.swarmos/mcp/servers.json` or via `swarm mcp add`):

```bash
swarm mcp add clinear --command clinear-mcp --env LINEAR_TOKEN=<YOUR_LINEAR_TOKEN>
```

**Codex CLI** (`~/.config/codex/mcp.json`):

```json
{
  "servers": {
    "clinear": {
      "command": "clinear-mcp",
      "env": { "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>" }
    }
  }
}
```

If `clinear-mcp` is not on the system `PATH` of the GUI app (common on macOS),
use the absolute path:

```json
{
  "mcpServers": {
    "clinear": {
      "command": "/home/you/.local/bin/clinear-mcp",
      "env": { "LINEAR_TOKEN": "<YOUR_LINEAR_TOKEN>" }
    }
  }
}
```

Find the absolute path with `which clinear-mcp`.

#### Step 4 — Verify the wiring

Restart the MCP client and confirm the server connects. From inside the
client you should see:

- **1 tool**: `clinear_guide`
- **2 concrete resources**: `clinear://me`, `clinear://issues/mine`
- **5 resource templates**: `clinear://issue/{id}`, `clinear://team/{key}`,
  `clinear://project/{id_or_slug}`, `clinear://cycle/current/{team_key}`,
  `clinear://issues/team/{team_key}`
- **6 prompts**: `triage`, `daily_standup`, `create_from_error`,
  `hand_off`, `cycle_review`, `issue_investigate`

If you have the MCP Inspector installed, you can also smoke-test from a
terminal:

```bash
npx @modelcontextprotocol/inspector clinear-mcp
```

This launches a browser UI that lets you list tools/resources/prompts and
invoke them interactively.

For a quick stdio sanity check without the Inspector:

```bash
(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}'
 echo '{"jsonrpc":"2.0","method":"notifications/initialized"}'
 echo '{"jsonrpc":"2.0","id":2,"method":"tools/list"}') | clinear-mcp | head -3
```

You should see a JSON-RPC initialize response followed by `tools/list`
returning `clinear_guide`.

#### Troubleshooting

| Symptom | Fix |
|---|---|
| `clinear-mcp: command not found` in GUI app | Use absolute path in the MCP config (`which clinear-mcp`) |
| Server starts but resource reads return auth error | Token not visible to the server — pass it via the config's `env` block instead of relying on shell `export` |
| `pip install 'clinear[mcp]'` fails with quoting error | Some shells eat the brackets — quote the whole spec or escape: `pip install clinear\[mcp\]` |
| Tool list is empty in client | Restart the MCP client after editing the config; some clients cache `tools/list` |
| Stdout looks corrupted | Don't run `clinear-mcp` interactively — it speaks JSON-RPC on stdin/stdout. Logs go to stderr. |
