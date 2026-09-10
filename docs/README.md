# gatling-mcp-server

An MCP server that exposes [gatling-server](https://github.com/jecklgamis/gatling-server)'s task API as MCP
tools over streamable-http, so an AI agent can submit a Gatling simulation, poll its status, and pull back logs
without anyone hand-writing curl.

This site covers **running and connecting to** a gatling-mcp-server instance. For building the project itself
(installing dependencies, running tests, project layout), see the
[repo's README](https://github.com/jecklgamis/gatling-mcp-server#readme).

## MCP Tools (`/gatling_mcp`)

| Tool                 | Description                                                                          |
|----------------------|---------------------------------------------------------------------------------------|
| `upload_jar`         | Upload a local jar file to gatling-server; returns an `id` and a ready-to-use `url`. Colocated setups only - see [Architecture](architecture.md#recommended-workflow) |
| `submit_task`        | Submit a Gatling simulation to run, given a simulation class, jar URL, and javaOpts   |
| `get_task_status`    | Get a task's current status (Started/Completed/Aborted, success, timestamps)         |
| `get_console_log`    | Get the raw JVM/Gatling console output for a task - useful for diagnosing failures    |
| `get_simulation_log` | Get Gatling's own simulation report for a completed task (binary on recent Gatling versions - prefer `get_console_log`) |
| `abort_task`         | Kill a currently running task                                                        |

Every tool is also mounted as a plain REST route (`GET` for read-only tools, `POST` for anything that mutates
state), and all routes require the `Authorization: Bearer <GATLING_MCP_API_TOKEN>` header.

## Where to go next

- **[Deployment](deployment.md)** - run it with Docker, deploy it to Kubernetes, or install a tagged release.
- **[Connecting Clients](clients.md)** - wire up Claude Code, Claude Desktop, Cursor, Windsurf, Cline, Gemini
  CLI, or JetBrains AI Assistant.
- **[Architecture](architecture.md)** - how gatling-mcp-server, gatling-server, and the example Gatling projects
  fit together, the local-vs-remote deployment tradeoff, and the recommended agent workflow.
