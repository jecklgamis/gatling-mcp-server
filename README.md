# gatling-mcp-server

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

Every tool is also mounted as a plain `GET` REST route with the same name and arguments (e.g. `GET /submit_task?
simulation=...&jar_url=...`), matching gatling-server's own `/task/*` shape - useful for testing without an LLM in
the loop.

**Caveat:** `get_simulation_log` returns whatever `gatling-server`'s `/task/simulationLog/{taskId}` hands back. On
recent Gatling versions that file is a binary format, not the classic text log - `get_console_log` is the more
reliable source for diagnosing a run from an AI agent today.

## Project Structure

```
server.py                — FastAPI app entry point with REST routes and MCP mount
server/                  — MCP server definitions
  gatling_tools.py       — Gatling MCP server: tool definitions, calls gatling-server's HTTP API
client/                  — LangChain agent client
  gatling_client.py      — Interactive LangChain agent client
  llm_factory.py         — LLM provider factory (ollama, openai, gemini, openrouter)
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

| Env Var                   | Description                                    | Default                 |
|----------------------------|-------------------------------------------------|--------------------------|
| `GATLING_SERVER_URL`       | Base URL of the gatling-server instance          | `http://localhost:58080` |
| `GATLING_SERVER_API_TOKEN` | Bearer token for gatling-server's `/task/*` API  | `default`                |

### Run Locally

```bash
pip install -r requirements.txt
python server.py
```

The server starts on `http://localhost:58090` with:
- Root endpoint at `/` listing available endpoints
- Gatling MCP endpoint at `/gatling_mcp` (streamable-http transport)
- REST API endpoints at `/upload_jar`, `/submit_task`, `/get_task_status`, `/get_console_log`,
  `/get_simulation_log`, `/abort_task`
- API docs at `/docs`

### Run Client

The client uses a LangChain agent to interact with the MCP server via an interactive REPL. Configure the LLM
provider via the `LLM_PROVIDER` env var and the server URL via `MCP_SERVER_URL`.

| Env Var          | Description         | Default                  |
|-------------------|----------------------|----------------------------|
| `LLM_PROVIDER`    | LLM provider to use  | `ollama`                   |
| `MCP_SERVER_URL`  | MCP server base URL  | `http://localhost:58090`   |

Supported LLM providers:

| Provider     | Model              |
|---------------|--------------------|
| `ollama`      | `llama3.2`         |
| `openai`      | `gpt-4.1-nano`     |
| `gemini`      | `gemini-2.5-flash` |
| `openrouter`  | `openrouter/free`  |

```bash
python -m client.gatling_client
```

```bash
LLM_PROVIDER=openai python -m client.gatling_client
```

Example queries once the REPL is up:

```
Query: upload target/gatling-scala-example.jar and run gatling.test.example.simulation.ExampleSimulation
       against http://localhost:8080 for 1 minute at 10 requests per second
Query: what's the status of the task you just submitted?
Query: it failed - show me the console log and tell me why
```

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

The GitHub Actions [workflow](.github/workflows/build.yaml) runs tests on pushes to `main` and on pull requests,
and pushes a Docker image to Docker Hub on non-PR events.
