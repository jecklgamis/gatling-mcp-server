import os

os.environ["GATLING_MCP_API_TOKEN"] = "test-token"

import httpx
import respx
from httpx import ASGITransport, Response

from server.app import app
from server.gatling_tools import GATLING_SERVER_URL

AUTH_HEADERS = {"Authorization": "Bearer test-token"}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def test_root_requires_auth():
    async with _client() as client:
        resp = await client.get("/")

    assert resp.status_code == 401


async def test_root_rejects_wrong_token():
    async with _client() as client:
        resp = await client.get("/", headers={"Authorization": "Bearer wrong-token"})

    assert resp.status_code == 401


async def test_root_succeeds_with_correct_token():
    async with _client() as client:
        resp = await client.get("/", headers=AUTH_HEADERS)

    assert resp.status_code == 200
    assert resp.json()["app_name"] == "gatling-mcp-server"


@respx.mock
async def test_read_only_tool_mounted_as_get():
    respx.get(f"{GATLING_SERVER_URL}/task/task-1").mock(
        return_value=Response(200, json={"Status": "Completed"})
    )

    async with _client() as client:
        resp = await client.get("/get_task_status", params={"task_id": "task-1"}, headers=AUTH_HEADERS)

    assert resp.status_code == 200
    assert resp.json()["Status"] == "Completed"


async def test_mutating_tool_rejects_get():
    async with _client() as client:
        resp = await client.get("/submit_task", headers=AUTH_HEADERS)

    assert resp.status_code == 405


@respx.mock
async def test_mutating_tool_mounted_as_post():
    respx.post(f"{GATLING_SERVER_URL}/task/submit").mock(
        return_value=Response(200, json={"ok": True, "taskId": "task-1"})
    )

    async with _client() as client:
        resp = await client.post(
            "/submit_task",
            params={"simulation": "com.example.Sim", "jar_url": "http://x/x.jar"},
            headers=AUTH_HEADERS,
        )

    assert resp.status_code == 200
    assert resp.json()["taskId"] == "task-1"
