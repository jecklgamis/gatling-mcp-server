# gatling-mcp-server

[![Build](https://github.com/jecklgamis/gatling-mcp-server/actions/workflows/build.yaml/badge.svg)](https://github.com/jecklgamis/gatling-mcp-server/actions/workflows/build.yaml)

A FastAPI MCP (Model Context Protocol) server built with [FastMCP](https://github.com/jlowin/fastmcp). Exposes
[gatling-server](https://github.com/jecklgamis/gatling-server)'s task API as MCP tools over streamable-http
transport, so an AI agent can upload a jar, submit a Gatling simulation, poll its status, and pull back logs -
without anyone hand-writing curl.

## MCP Tools (`/gatling_mcp`)

| Tool                 | Description                                                                          |
|----------------------|---------------------------------------------------------------------------------------|
| `upload_jar`         | Upload a local jar file to gatling-server; returns an `id` and a ready-to-use `url`   |
| `submit_task`        | Submit a Gatling simulation to run, given a simulation class, jar URL, and javaOpts   |
| `get_task_status`    | Get a task's current status (Started/Completed/Aborted, success, timestamps)         |
| `get_console_log`    | Get the raw JVM/Gatling console output for a task - useful for diagnosing failures    |
| `get_simulation_log` | Get Gatling's own simulation report for a completed task (binary on recent Gatling versions - prefer `get_console_log`) |
| `abort_task`         | Kill a currently running task                                                        |

Every tool is also mounted as a plain REST route (`GET` for read-only tools, `POST` for anything that mutates
state), and all routes require the `Authorization: Bearer <GATLING_MCP_API_TOKEN>` header described below.

## Getting Started

### Requirements

* Python 3.13+
* A running [gatling-server](https://github.com/jecklgamis/gatling-server) instance

### Configuration

| Env Var                       | Description                                                   | Default                  |
|--------------------------------|-----------------------------------------------------------------|----------------------------|
| `GATLING_SERVER_URL`           | Base URL of the gatling-server instance                        | `http://localhost:58080` |
| `GATLING_SERVER_API_TOKEN`     | Bearer token for gatling-server's `/task/*` API                | `default`                |
| `GATLING_MCP_API_TOKEN`        | Bearer token required on every request to **this** server (MCP and REST alike) | `default` |
| `GATLING_MCP_REQUEST_TIMEOUT`  | Timeout (seconds) for lightweight calls (submit/status/logs/abort) | `30`                  |
| `GATLING_MCP_UPLOAD_TIMEOUT`   | Timeout (seconds) for `upload_jar`, which can move tens of MB  | `300`                    |

### Run Locally

```bash
pip install -r requirements.txt
python server.py
```

Or `./run-server.sh`, which applies the defaults from the table above.

### Run with Docker

```bash
docker build -t gatling-mcp-server .
docker run -p 58090:58090 --add-host=host.docker.internal:host-gateway \
  -e GATLING_SERVER_URL=http://host.docker.internal:58080 gatling-mcp-server
```

`--add-host` is required on Linux for `host.docker.internal` to resolve; Docker Desktop (Mac/Windows) provides it
automatically and the flag is a harmless no-op there.

### Install from a GitHub Release

```bash
pip install https://github.com/jecklgamis/gatling-mcp-server/releases/download/v1.2.3/gatling_mcp_server-1.2.3-py3-none-any.whl
export GATLING_MCP_API_TOKEN=... GATLING_SERVER_URL=... GATLING_SERVER_API_TOKEN=...
gatling-mcp-server
```

### Connect from Claude Code

Once the server is running, register it as a project-scoped MCP server in any repo you work from (e.g.
[gatling-scala-example](https://github.com/jecklgamis/gatling-scala-example) or
[gatling-java-example](https://github.com/jecklgamis/gatling-java-example)):

```bash
cd /path/to/gatling-scala-example
claude mcp add --transport http gatling-mcp-server http://localhost:58090/gatling_mcp -s project \
  -H "Authorization: Bearer \${GATLING_MCP_API_TOKEN}"
```

This writes a `.mcp.json` in that repo:

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "type": "http",
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer ${GATLING_MCP_API_TOKEN}"
      }
    }
  }
}
```

`${GATLING_MCP_API_TOKEN}` is expanded from your own shell environment at connect time, not stored literally - so
`.mcp.json` itself contains no secret and is safe to commit and share with the team. Whoever opens Claude Code in
that repo just needs `GATLING_MCP_API_TOKEN` set in their own environment; they're then prompted to trust/enable the
`gatling-mcp-server` server automatically. Run `claude mcp list` to confirm it connects.

Omit `-s project` (or use `-s user`) to register it in your personal config instead, if you'd rather it be available
across every project rather than shared via the repo.

### Connect from Other MCP Clients

Any MCP client that supports the streamable-http transport can call this server the same way - point it at
`http://localhost:58090/gatling_mcp` with an `Authorization: Bearer <GATLING_MCP_API_TOKEN>` header. A few common
ones:

**Claude Desktop** - add to `claude_desktop_config.json` (Settings -> Developer -> Edit Config):

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "type": "http",
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

**Cursor** - add to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

**Windsurf** - add to `~/.codeium/windsurf/mcp_config.json` (Windsurf Settings -> Cascade -> MCP Servers -> View raw
config), same shape as Cursor's above.

**Cline** (VS Code extension) - open the MCP Servers panel -> Configure MCP Servers, which opens
`cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "type": "streamableHttp",
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

**Gemini CLI** - add via `gemini mcp add`, or edit `~/.gemini/settings.json` (global) / `.gemini/settings.json`
(project) directly. Gemini CLI distinguishes streamable-http servers with `httpUrl` (as opposed to `url`, which is
SSE):

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "httpUrl": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

or equivalently: `gemini mcp add --transport http gatling-mcp-server http://localhost:58090/gatling_mcp -H "Authorization: Bearer <GATLING_MCP_API_TOKEN>"`.

**JetBrains AI Assistant** (IntelliJ IDEA, PyCharm, etc.) - Settings -> Tools -> AI Assistant -> Model Context
Protocol (MCP) -> Add, then switch the dialog to "As JSON":

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

Unlike Claude Code's `${GATLING_MCP_API_TOKEN}` shell expansion, these clients don't expand env vars in their config
files - substitute the actual token value, and avoid committing it to a shared/project-scoped config.

### Local vs. Remote Deployment

`upload_jar` and `submit_task` have different locality requirements, because only one of them actually moves file
bytes through this server:

- **`submit_task`** just hands gatling-server a URL (`http://...`, `https://...`, or `s3://...`) and gatling-server
  downloads it directly, server-side, subject to its own `taskSubmit.allowedHttpHosts`/S3-bucket allowlists. No jar
  bytes ever pass through gatling-mcp-server or the MCP client. If your jar already has a URL (published by CI to
  S3, an artifact repo, etc.), gatling-mcp-server can run anywhere - a shared team instance, a remote host, a
  container - with no locality constraint at all.

- **`upload_jar`** takes a `file_path` argument, which is just a string passed over MCP - the file's *bytes* are
  never sent over the MCP protocol. gatling-mcp-server opens that path **on its own local disk** and streams the
  bytes to gatling-server's `/upload` endpoint itself. That means `file_path` must be resolvable from wherever the
  **gatling-mcp-server process** runs, not from wherever the MCP client (Claude, an IDE, etc.) happens to be
  running. If gatling-mcp-server is remote and your jar only exists as a local build artifact you haven't published
  anywhere, `upload_jar` will simply fail with "no such file."

**Practical guidance:**

- Building and testing locally (the common case today): run gatling-mcp-server **on the same machine** where you
  build the jar (e.g. alongside `gatling-scala-example`/`gatling-java-example`), and use `upload_jar` with an
  absolute path to the build output. This is what the setup in this repo's examples assumes.
- Sharing one gatling-mcp-server across a team, or driving it from a hosted/remote MCP client: either always
  publish jars to a URL first (S3, CI artifacts, gatling-server's own `/uploads/` via a direct `curl`) and use
  `submit_task` alone, or accept that `upload_jar` only works for whoever is colocated with that gatling-mcp-server
  instance. Making `upload_jar` accept file bytes/base64 over MCP instead of a local path (removing the locality
  requirement entirely) is a possible future enhancement, not implemented today.

