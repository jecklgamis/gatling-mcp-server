import os
from pathlib import Path

import httpx
from fastmcp import FastMCP

mcp = FastMCP("Gatling Server", instructions="Submit, monitor and inspect Gatling load test runs on gatling-server.")

GATLING_SERVER_URL = os.environ.get("GATLING_SERVER_URL", "http://localhost:58080").rstrip("/")
GATLING_SERVER_API_TOKEN = os.environ.get("GATLING_SERVER_API_TOKEN", "default")

_AUTH_HEADER = {"Authorization": f"Bearer {GATLING_SERVER_API_TOKEN}"}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=GATLING_SERVER_URL, headers=_AUTH_HEADER, timeout=30)


async def _upload_jar(file_path: str) -> dict:
    """Upload a jar file to gatling-server, returning an id that can be used
    to build a URL for submit_task's jar_url argument
    (e.g. "<GATLING_SERVER_URL>/uploads/<id>/<filename>").

    Args:
        file_path: Path to the jar file on disk, readable by this MCP server.
    """
    path = Path(file_path)
    if not path.is_file():
        return {"error": f"no such file: {file_path}"}
    async with _client() as client:
        with path.open("rb") as f:
            resp = await client.post("/upload", files={"file": (path.name, f, "application/octet-stream")})
        if resp.status_code != 200:
            return {"error": f"upload failed with status {resp.status_code}", "body": resp.text}
        body = resp.json()
        body["url"] = f"{GATLING_SERVER_URL}/uploads/{body['id']}/{path.name}"
        return body


async def _submit_task(simulation: str, jar_url: str, java_opts: str = "") -> dict:
    """Submit a Gatling simulation to run. jar_url may be an http(s) URL
    (e.g. one returned by upload_jar) or an s3:// URL, subject to
    gatling-server's configured allowlists.

    Args:
        simulation: Fully-qualified Gatling simulation class name.
        jar_url: URL of the jar containing the simulation.
        java_opts: Space-separated JVM system properties/flags for the run
            (e.g. "-DbaseUrl=http://example.com -DdurationMin=1 -DrequestPerSecond=10").
    """
    async with _client() as client:
        resp = await client.post(
            "/task/submit",
            json={"simulation": simulation, "javaOpts": java_opts, "url": jar_url},
        )
        if resp.status_code != 200:
            return {"error": f"submit failed with status {resp.status_code}", "body": resp.text}
        return resp.json()


async def _get_task_status(task_id: str) -> dict:
    """Get a submitted task's current status (Started/Completed/Aborted, success, timestamps).

    Args:
        task_id: The task id returned by submit_task.
    """
    async with _client() as client:
        resp = await client.get(f"/task/{task_id}")
        if resp.status_code != 200:
            return {"error": f"status check failed with status {resp.status_code}", "body": resp.text}
        return resp.json()


async def _get_console_log(task_id: str) -> str:
    """Get the raw JVM/Gatling console output for a task - useful for
    diagnosing why a run failed (stack traces, connection errors, etc).

    Args:
        task_id: The task id returned by submit_task.
    """
    async with _client() as client:
        resp = await client.get(f"/task/console/{task_id}")
        if resp.status_code != 200:
            return f"error: console log fetch failed with status {resp.status_code}: {resp.text}"
        return resp.text


async def _get_simulation_log(task_id: str) -> str:
    """Get Gatling's own simulation report (throughput, latency percentiles,
    KO/OK breakdown) for a completed task.

    Args:
        task_id: The task id returned by submit_task.
    """
    async with _client() as client:
        resp = await client.get(f"/task/simulationLog/{task_id}")
        if resp.status_code != 200:
            return f"error: simulation log fetch failed with status {resp.status_code}: {resp.text}"
        return resp.text


async def _abort_task(task_id: str) -> dict:
    """Kill a currently running task.

    Args:
        task_id: The task id returned by submit_task.
    """
    async with _client() as client:
        resp = await client.post(f"/task/abort/{task_id}")
        if resp.status_code != 200:
            return {"error": f"abort failed with status {resp.status_code}", "body": resp.text}
        return {"ok": True}


mcp.tool()(_upload_jar)
mcp.tool()(_submit_task)
mcp.tool()(_get_task_status)
mcp.tool()(_get_console_log)
mcp.tool()(_get_simulation_log)
mcp.tool()(_abort_task)

gatling_tools = [_upload_jar, _submit_task, _get_task_status, _get_console_log, _get_simulation_log, _abort_task]
