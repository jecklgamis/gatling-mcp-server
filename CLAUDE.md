# CLAUDE.md

## Project Overview

This is a FastAPI MCP (Model Context Protocol) server built with FastMCP. It exposes gatling-server's task API
(upload jar, submit simulation, poll status, fetch logs, abort) as MCP tools over streamable-http transport on port
58090. Includes a LangChain-based client for interacting with the server via an LLM agent.

Sibling projects:
- `../gatling-server` — the Go server this project talks to (its REST API is the thing being wrapped).
- `../gatling-scala-example` — an example Gatling simulation project, useful for producing a jar to test with.

## Tech Stack

- Python 3.13+
- FastMCP
- FastAPI / Uvicorn
- httpx (calling gatling-server)
- LangChain / LangGraph (client)
- langchain-mcp-adapters (client)
- pytest + pytest-asyncio + respx (tests)

## Project Structure

- `server.py` — FastAPI app entry point with REST routes and MCP mount
- `server/gatling_tools.py` — tool definitions; each tool calls gatling-server's HTTP API via httpx
- `client/gatling_client.py` — LangChain agent client for the gatling MCP
- `client/llm_factory.py` — LLM provider factory (ollama, openai, gemini, openrouter)
- `tests/test_gatling_tools.py` — tests for the tool functions, gatling-server calls mocked via respx
- `requirements.txt` — pinned Python dependencies
- `Dockerfile` — container image definition (port 58090)
- `.github/workflows/build.yaml` — CI/CD pipeline (test, build, Docker push)

## Configuration

- `GATLING_SERVER_URL` (default `http://localhost:58080`) - base URL of the gatling-server instance to call.
- `GATLING_SERVER_API_TOKEN` (default `default`) - bearer token for gatling-server's `/task/*` endpoints.

## Running

```bash
pip install -r requirements.txt
python server.py
```

## Testing

```bash
pytest -s
```

## Docker

```bash
docker build -t gatling-mcp-server .
docker run -p 58090:58090 gatling-mcp-server
```

## Known limitations

- `get_simulation_log` returns whatever gatling-server's `/task/simulationLog/{taskId}` hands back, which on recent
  Gatling versions is a binary format, not text. `get_console_log` is the reliable one for now.
- `upload_jar` reads a local file path, so it assumes the MCP server runs on the same machine (or a shared
  filesystem) as the jar being uploaded.
- No `list_uploads`/task-history tool yet - gatling-server doesn't expose a JSON listing endpoint for either today.
