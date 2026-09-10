# gatling-mcp-server

[![Build](https://github.com/jecklgamis/gatling-mcp-server/actions/workflows/build.yaml/badge.svg)](https://github.com/jecklgamis/gatling-mcp-server/actions/workflows/build.yaml)

A FastAPI MCP (Model Context Protocol) server built with [FastMCP](https://github.com/jlowin/fastmcp). Exposes
[gatling-server](https://github.com/jecklgamis/gatling-server)'s task API as MCP tools over streamable-http
transport, so an AI agent can upload a jar, submit a Gatling simulation, poll its status, and pull back logs -
without anyone hand-writing curl.

This README covers **developing** gatling-mcp-server. For running, deploying, and connecting clients to it, see
the docs site: **[jecklgamis.github.io/gatling-mcp-server](https://jecklgamis.github.io/gatling-mcp-server/)**
(or browse [`docs/`](docs) directly).

## MCP Tools (`/gatling_mcp`)

| Tool                 | Description                                                                          |
|----------------------|---------------------------------------------------------------------------------------|
| `upload_jar`         | Upload a local jar file to gatling-server; returns an `id` and a ready-to-use `url`. Colocated setups only - see [Architecture docs](docs/architecture.md#recommended-workflow) |
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

### Testing

```bash
pytest -s
```

## Documentation

Running Docker/Kubernetes, installing a tagged release, connecting MCP clients (Claude Code, Claude Desktop,
Cursor, Windsurf, Cline, Gemini CLI, JetBrains AI Assistant), and the local-vs-remote-deployment/recommended
agent workflow rationale all live in the docs site:
**[jecklgamis.github.io/gatling-mcp-server](https://jecklgamis.github.io/gatling-mcp-server/)** (source in
[`docs/`](docs)).
