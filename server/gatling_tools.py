import logging
import os
from pathlib import Path

import httpx
from fastmcp import FastMCP

logger = logging.getLogger("gatling_mcp_server")

mcp = FastMCP("Gatling Server", instructions="Submit, monitor and inspect Gatling load test runs on gatling-server.")

GATLING_SERVER_URL = os.environ.get("GATLING_SERVER_URL", "http://localhost:58080").rstrip("/")
GATLING_SERVER_API_TOKEN = os.environ.get("GATLING_SERVER_API_TOKEN", "default")

_AUTH_HEADER = {"Authorization": f"Bearer {GATLING_SERVER_API_TOKEN}"}

# Most calls (submit/status/logs/abort) are small and fast; jar uploads can be
# tens of MB and take much longer, especially over a slow uplink to a remote
# gatling-server - 30s was measured to be nowhere near enough for a 50MB jar
# on an ordinary connection (it took ~100s), so uploads get their own, much
# longer budget.
REQUEST_TIMEOUT = float(os.environ.get("GATLING_MCP_REQUEST_TIMEOUT", "30"))
UPLOAD_TIMEOUT = float(os.environ.get("GATLING_MCP_UPLOAD_TIMEOUT", "300"))


def _client(timeout: float = REQUEST_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=GATLING_SERVER_URL, headers=_AUTH_HEADER, timeout=timeout)


def _network_error(action: str, exc: Exception) -> dict:
    return {"error": f"{action} failed: {exc.__class__.__name__}: {exc}"}


def _upstream_error(action: str, resp: httpx.Response) -> dict:
    logger.error("%s failed with status %s: %s", action, resp.status_code, resp.text)
    return {"error": f"{action} failed with status {resp.status_code}"}


def _upstream_error_str(action: str, resp: httpx.Response) -> str:
    logger.error("%s failed with status %s: %s", action, resp.status_code, resp.text)
    return f"error: {action} failed with status {resp.status_code}"


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
    try:
        async with _client(timeout=UPLOAD_TIMEOUT) as client:
            with path.open("rb") as f:
                resp = await client.post("/upload", files={"file": (path.name, f, "application/octet-stream")})
    except httpx.HTTPError as exc:
        return _network_error("upload", exc)
    if resp.status_code != 200:
        return _upstream_error("upload", resp)
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
    try:
        async with _client() as client:
            resp = await client.post(
                "/task/submit",
                json={"simulation": simulation, "javaOpts": java_opts, "url": jar_url},
            )
    except httpx.HTTPError as exc:
        return _network_error("submit", exc)
    if resp.status_code != 200:
        return _upstream_error("submit", resp)
    return resp.json()


async def _get_task_status(task_id: str) -> dict:
    """Get a submitted task's current status (Started/Completed/Aborted, success, timestamps).

    Args:
        task_id: The task id returned by submit_task.
    """
    try:
        async with _client() as client:
            resp = await client.get(f"/task/{task_id}")
    except httpx.HTTPError as exc:
        return _network_error("status check", exc)
    if resp.status_code != 200:
        return _upstream_error("status check", resp)
    return resp.json()


async def _get_console_log(task_id: str) -> str:
    """Get the raw JVM/Gatling console output for a task - useful for
    diagnosing why a run failed (stack traces, connection errors, etc).

    Args:
        task_id: The task id returned by submit_task.
    """
    try:
        async with _client() as client:
            resp = await client.get(f"/task/console/{task_id}")
    except httpx.HTTPError as exc:
        return f"error: console log fetch failed: {exc.__class__.__name__}: {exc}"
    if resp.status_code != 200:
        return _upstream_error_str("console log fetch", resp)
    return resp.text


async def _get_simulation_log(task_id: str) -> str:
    """Get Gatling's own simulation report (throughput, latency percentiles,
    KO/OK breakdown) for a completed task.

    Args:
        task_id: The task id returned by submit_task.
    """
    try:
        async with _client() as client:
            resp = await client.get(f"/task/simulationLog/{task_id}")
    except httpx.HTTPError as exc:
        return f"error: simulation log fetch failed: {exc.__class__.__name__}: {exc}"
    if resp.status_code != 200:
        return _upstream_error_str("simulation log fetch", resp)
    return resp.text


async def _abort_task(task_id: str) -> dict:
    """Kill a currently running task.

    Args:
        task_id: The task id returned by submit_task.
    """
    try:
        async with _client() as client:
            resp = await client.post(f"/task/abort/{task_id}")
    except httpx.HTTPError as exc:
        return _network_error("abort", exc)
    if resp.status_code != 200:
        return _upstream_error("abort", resp)
    return {"ok": True}


mcp.tool(name="upload_jar")(_upload_jar)
mcp.tool(name="submit_task")(_submit_task)
mcp.tool(name="get_task_status")(_get_task_status)
mcp.tool(name="get_console_log")(_get_console_log)
mcp.tool(name="get_simulation_log")(_get_simulation_log)
mcp.tool(name="abort_task")(_abort_task)

gatling_tools = [_upload_jar, _submit_task, _get_task_status, _get_console_log, _get_simulation_log, _abort_task]
