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
| `get_simulation_log` | Get Gatling's own simulation report for a completed task (see caveat below)          |
| `abort_task`         | Kill a currently running task                                                        |

Every tool is also mounted as a plain REST route with the same name and arguments - `GET` for read-only tools
(`get_task_status`, `get_console_log`, `get_simulation_log`), `POST` for anything that mutates state
(`upload_jar`, `submit_task`, `abort_task`, e.g. `POST /submit_task?simulation=...&jar_url=...`) so those can't be
triggered by a bare link/image tag. Useful for testing without an LLM in the loop.

All routes - MCP and REST alike - require the `Authorization: Bearer <GATLING_MCP_API_TOKEN>` header described below.

**Caveat:** `get_simulation_log` returns whatever `gatling-server`'s `/task/simulationLog/{taskId}` hands back. On
recent Gatling versions that file is a binary format, not the classic text log - `get_console_log` is the more
reliable source for diagnosing a run from an AI agent today.

## Project Structure

```
server.py                — FastAPI app entry point with REST routes and MCP mount
server/                  — MCP server definitions
  gatling_tools.py       — Gatling MCP server: tool definitions, calls gatling-server's HTTP API
tests/                   — pytest tests for the tool functions (gatling-server calls mocked via respx)
requirements.txt         — Python dependencies
Dockerfile                — Container image definition
Makefile                  — Build and run shortcuts
```

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

`GATLING_MCP_API_TOKEN` defaults to `"default"` for local dev convenience, but the server logs a warning on startup
if it's left unset - **always set it explicitly before running this anywhere reachable beyond localhost.** Without
it, anyone who can reach this server can invoke any tool using the credentials baked into its own environment,
including `upload_jar` with an arbitrary local `file_path`.

### Run Locally

```bash
pip install -r requirements.txt
python server.py
```

Or use `./run-server.sh`, which sets the same defaults shown in the table above for any of these env vars you
haven't already set yourself (`GATLING_SERVER_URL`, `GATLING_SERVER_API_TOKEN`, `GATLING_MCP_API_TOKEN`,
`GATLING_MCP_REQUEST_TIMEOUT`, `GATLING_MCP_UPLOAD_TIMEOUT`) before starting the server.

The server starts on `http://localhost:58090` with:
- Root endpoint at `/` listing available endpoints
- Gatling MCP endpoint at `/gatling_mcp` (streamable-http transport)
- REST API endpoints at `/upload_jar`, `/submit_task`, `/get_task_status`, `/get_console_log`,
  `/get_simulation_log`, `/abort_task`
- API docs at `/docs`

### Connect from Claude Code

Once the server is running, register it as a project-scoped MCP server in any repo you work from (e.g.
[gatling-scala-example](https://github.com/jecklgamis/gatling-scala-example) or
[gatling-java-example](https://github.com/jecklgamis/gatling-java-example)):

```bash
cd /path/to/gatling-scala-example
claude mcp add --transport http gatling http://localhost:58090/gatling_mcp -s project \
  -H "Authorization: Bearer \${GATLING_MCP_API_TOKEN}"
```

This writes a `.mcp.json` in that repo:

```json
{
  "mcpServers": {
    "gatling": {
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
`gatling` server automatically. Run `claude mcp list` to confirm it connects.

Omit `-s project` (or use `-s user`) to register it in your personal config instead, if you'd rather it be available
across every project rather than shared via the repo.

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

### Run with Docker

```bash
docker build -t gatling-mcp-server .
docker run -p 58090:58090 -e GATLING_SERVER_URL=http://host.docker.internal:58080 gatling-mcp-server
```

## Makefile Targets

| Target          | Description                              |
|------------------|--------------------------------------------|
| `install-deps`   | Install Python dependencies                |
| `image`          | Build Docker image                         |
| `run`            | Run Docker container                       |
| `run-shell`      | Start a shell in a new container           |
| `exec-shell`     | Exec into a running container              |
| `check`          | Run tests with pytest                      |
| `clean`          | Remove generated files                     |
| `up`             | Build and run (`check` + `image` + `run`)  |

## CI/CD

Two workflows:

- [`build.yaml`](.github/workflows/build.yaml) - runs tests on every push to `main`, on pull requests, and on `v*`
  tag pushes. On `main` and tag pushes (not PRs) it also builds and pushes a Docker image to both Docker Hub
  (`jecklgamis/gatling-mcp-server`) and GHCR (`ghcr.io/jecklgamis/gatling-mcp-server`): `main` pushes update the
  `:latest` tag, and `v*` tag pushes produce immutable semver tags (`v1.2.3` -> `1.2.3` and `1.2`) instead of a
  floating branch tag.
- [`release.yaml`](.github/workflows/release.yaml) - fires on the same `v*` tag pushes and creates a GitHub Release
  with auto-generated notes (`gh release create --generate-notes`), marked as a pre-release if the tag contains a
  hyphen (e.g. `v1.0.0-rc.1`).

### Cutting a release

```bash
git tag v1.2.3
git push origin v1.2.3
```

That single tag push is enough - `build.yaml` builds and pushes the versioned image, and `release.yaml` creates the
GitHub Release page with notes, in parallel.
