import httpx
import respx
from httpx import Response

from server.gatling_tools import (
    GATLING_SERVER_URL,
    _abort_task,
    _get_console_log,
    _get_simulation_log,
    _get_task_status,
    _submit_task,
    _upload_jar,
)


@respx.mock
async def test_upload_jar_success(tmp_path):
    jar = tmp_path / "example.jar"
    jar.write_bytes(b"fake-jar-content")
    respx.post(f"{GATLING_SERVER_URL}/upload").mock(
        return_value=Response(200, json={"id": "abc-123"})
    )

    result = await _upload_jar(str(jar))

    assert result["id"] == "abc-123"
    assert result["url"] == f"{GATLING_SERVER_URL}/uploads/abc-123/example.jar"


async def test_upload_jar_missing_file():
    result = await _upload_jar("/no/such/file.jar")
    assert "error" in result


@respx.mock
async def test_upload_jar_failure_response(tmp_path):
    jar = tmp_path / "example.jar"
    jar.write_bytes(b"fake-jar-content")
    respx.post(f"{GATLING_SERVER_URL}/upload").mock(return_value=Response(401, text="unauthorized"))

    result = await _upload_jar(str(jar))

    assert "error" in result
    assert "401" in result["error"]


@respx.mock
async def test_submit_task_success():
    respx.post(f"{GATLING_SERVER_URL}/task/submit").mock(
        return_value=Response(200, json={"ok": True, "taskId": "task-1"})
    )

    result = await _submit_task("com.example.SomeSimulation", "http://localhost:58080/uploads/x/x.jar", "-Dfoo=bar")

    assert result == {"ok": True, "taskId": "task-1"}


@respx.mock
async def test_submit_task_failure():
    respx.post(f"{GATLING_SERVER_URL}/task/submit").mock(return_value=Response(400, text="bad request"))

    result = await _submit_task("com.example.SomeSimulation", "http://bad-host/x.jar")

    assert "error" in result


@respx.mock
async def test_get_task_status_success():
    respx.get(f"{GATLING_SERVER_URL}/task/task-1").mock(
        return_value=Response(200, json={"Status": "Completed", "Success": True})
    )

    result = await _get_task_status("task-1")

    assert result["Status"] == "Completed"


@respx.mock
async def test_get_console_log_success():
    respx.get(f"{GATLING_SERVER_URL}/task/console/task-1").mock(return_value=Response(200, text="some console output"))

    result = await _get_console_log("task-1")

    assert result == "some console output"


@respx.mock
async def test_get_simulation_log_success():
    respx.get(f"{GATLING_SERVER_URL}/task/simulationLog/task-1").mock(return_value=Response(200, text="some sim log"))

    result = await _get_simulation_log("task-1")

    assert result == "some sim log"


@respx.mock
async def test_abort_task_success():
    respx.post(f"{GATLING_SERVER_URL}/task/abort/task-1").mock(return_value=Response(200))

    result = await _abort_task("task-1")

    assert result == {"ok": True}


@respx.mock
async def test_abort_task_failure():
    respx.post(f"{GATLING_SERVER_URL}/task/abort/task-1").mock(return_value=Response(404, text="not found"))

    result = await _abort_task("task-1")

    assert "error" in result


@respx.mock
async def test_upload_jar_timeout_returns_error_instead_of_raising(tmp_path):
    jar = tmp_path / "example.jar"
    jar.write_bytes(b"fake-jar-content")
    respx.post(f"{GATLING_SERVER_URL}/upload").mock(side_effect=httpx.ConnectTimeout("timed out"))

    result = await _upload_jar(str(jar))

    assert "error" in result
    assert "ConnectTimeout" in result["error"]


@respx.mock
async def test_submit_task_connection_error_returns_error_instead_of_raising():
    respx.post(f"{GATLING_SERVER_URL}/task/submit").mock(side_effect=httpx.ConnectError("refused"))

    result = await _submit_task("com.example.SomeSimulation", "http://localhost:58080/uploads/x/x.jar")

    assert "error" in result
    assert "ConnectError" in result["error"]


@respx.mock
async def test_get_console_log_network_error_returns_error_string_instead_of_raising():
    respx.get(f"{GATLING_SERVER_URL}/task/console/task-1").mock(side_effect=httpx.ReadTimeout("timed out"))

    result = await _get_console_log("task-1")

    assert result.startswith("error:")
    assert "ReadTimeout" in result
