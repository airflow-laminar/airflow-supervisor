import json
from datetime import UTC, datetime, timedelta
from threading import Thread
from unittest.mock import Mock, patch
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

import pytest
from hydra.utils import instantiate
from omegaconf import OmegaConf
from supervisor_pydantic import ProcessInfo

from airflow_supervisor import SupervisorViewerConfiguration, collect_supervisor_status
from airflow_supervisor.airflow.viewer import InstanceObservation, SupervisorSnapshot
from airflow_supervisor.ui.viewer import load_snapshot, render_viewer


def process(state=20):
    return ProcessInfo(
        name="worker",
        group="service",
        state=state,
        description="test",
        start=0,
        stop=0,
        now=0,
        exitstatus=0,
        logfile="",
        stdout_logfile="",
        stderr_logfile="",
        pid=123 if state == 20 else 0,
    )


@pytest.fixture
def storage():
    values = {}
    with (
        patch("airflow_supervisor.airflow.viewer._variable_get", side_effect=lambda key: values.get(key)),
        patch("airflow_supervisor.airflow.viewer._variable_set", side_effect=values.__setitem__),
    ):
        yield values


def test_collection_isolates_failures_preserves_last_observation_and_hides_credentials(storage):
    cfg = SupervisorViewerConfiguration(
        instances={
            name: {
                "cfg": {
                    "host": host,
                    "port": f"*:{port}",
                    "program": {},
                    "username": "rpc-user",
                    "password": "rpc-secret",
                }
            }
            for name, host, port in [
                ("host-a/main", "host-a", 9001),
                ("host-a/other", "host-a", 9011),
                ("host-b/main", "host-b", 9001),
            ]
        }
    )
    clients = {
        port: Mock(_rpcurl=f"http://localhost:{port}/RPC2", getAllProcessInfo=Mock(return_value=[process()]))
        for port in [9001, 9011]
    }
    with patch(
        "airflow_supervisor.airflow.viewer.SupervisorRemoteXMLRPCClient",
        side_effect=lambda cfg: clients[int(cfg.port.rsplit(":", 1)[-1])],
    ):
        assert all(collect_supervisor_status(cfg).values())
        before = storage[cfg.variable_key]["instances"][1]
        clients[9011].getAllProcessInfo.side_effect = OSError("rpc-user:rpc-secret@host-a")
        result = collect_supervisor_status(cfg)
    assert result == {"host-a/main": True, "host-a/other": False, "host-b/main": True}
    snapshot = SupervisorSnapshot.model_validate(storage[cfg.variable_key])
    failed = snapshot.instances[1]
    assert failed.observed_at is not None
    assert failed.observed_at.isoformat().replace("+00:00", "Z") == before["observed_at"]
    assert failed.processes[0].pid == 123
    assert failed.error == "XML-RPC request failed (OSError)"
    assert "rpc-secret" not in json.dumps(storage) and "rpc-user" not in json.dumps(storage)
    assert clients[9001].getAllProcessInfo.call_count == 4


def test_changed_endpoint_does_not_retain_previous_processes(storage):
    cfg = SupervisorViewerConfiguration(instances={"one": {"cfg": {"host": "old", "program": {}}}})
    client = Mock(_rpcurl="http://localhost:9001/RPC2", getAllProcessInfo=Mock(return_value=[process()]))
    with patch("airflow_supervisor.airflow.viewer.SupervisorRemoteXMLRPCClient", return_value=client):
        collect_supervisor_status(cfg)
        cfg.instances["one"].cfg.host = "replacement"
        client.getAllProcessInfo.side_effect = TimeoutError()
        collect_supervisor_status(cfg)
    value = storage[cfg.variable_key]["instances"][0]
    assert not value["processes"] and value["observed_at"] is None


def test_real_xmlrpc_probe_isolates_malformed_responses_and_only_reads_processes(storage):
    calls = []

    class Handler(SimpleXMLRPCRequestHandler):
        def do_POST(self):
            assert self.headers["Authorization"] == "Basic cmVhZGVyOnNlY3JldA=="
            if self.path == "/not-xml":
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.send_header("Content-Length", "7")
                self.end_headers()
                self.wfile.write(b"not XML")
                return
            super().do_POST()

    with SimpleXMLRPCServer(("127.0.0.1", 0), requestHandler=Handler, logRequests=False) as server:

        def inspect():
            calls.append("getAllProcessInfo")
            data = process(0).model_dump(mode="json")
            data.update(start=0, stop=0, now=0)
            return [data]

        server.register_function(inspect, "supervisor.getAllProcessInfo")
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            cfg = SupervisorViewerConfiguration(
                instances={
                    "live": {
                        "cfg": {
                            "host": "127.0.0.1",
                            "port": f"*:{server.server_address[1]}",
                            "username": "reader",
                            "password": "secret",
                            "program": {},
                        }
                    }
                }
            )
            malformed = cfg.instances["live"].model_copy(deep=True)
            malformed.cfg.rpcpath = "/not-xml"
            cfg.instances["malformed"] = malformed
            assert collect_supervisor_status(cfg) == {"live": True, "malformed": False}
        finally:
            server.shutdown()
            thread.join()
    assert calls == ["getAllProcessInfo"]
    assert storage[cfg.variable_key]["instances"][0]["processes"][0]["state"] == 0
    assert storage[cfg.variable_key]["instances"][1]["error"] == "XML-RPC request failed (ExpatError)"


def test_timeout_is_bounded_and_does_not_block_another_instance(storage):
    import socket

    with socket.socket() as stalled:
        stalled.bind(("127.0.0.1", 0))
        stalled.listen()
        cfg = SupervisorViewerConfiguration(
            timeout=0.05,
            instances={
                "stalled": {"cfg": {"host": "127.0.0.1", "port": f"*:{stalled.getsockname()[1]}", "program": {}}},
                "refused": {"cfg": {"host": "127.0.0.1", "port": "*:1", "program": {}}},
            },
        )
        assert collect_supervisor_status(cfg) == {"stalled": False, "refused": False}
    errors = [value["error"] for value in storage[cfg.variable_key]["instances"]]
    assert "TimeoutError" in errors[0] and "ConnectionRefusedError" in errors[1]


def test_render_distinguishes_stopped_unreachable_and_stale_and_escapes_text():
    now = datetime.now(UTC)
    snapshot = SupervisorSnapshot(
        collected_at=now,
        max_age=120,
        instances=[
            InstanceObservation(
                instance_id="host-a/main",
                host="host-a",
                port=9001,
                attempted_at=now,
                observed_at=now,
                reachable=True,
                processes=[process(0)],
                run_url="https://airflow.example/dags/service/runs/manual__example",
                log_url="https://airflow.example/dags/service/grid?tab=logs",
            ),
            InstanceObservation(
                instance_id="host-a/other",
                host="host-a",
                port=9011,
                attempted_at=now,
                observed_at=now - timedelta(minutes=5),
                error="<script>bad</script>",
                processes=[process()],
            ),
            InstanceObservation(
                instance_id="host-b/main",
                host="host-b",
                port=9001,
                attempted_at=now - timedelta(minutes=5),
                observed_at=now - timedelta(minutes=5),
                reachable=True,
                processes=[process()],
            ),
        ],
    )
    html = render_viewer(snapshot)
    assert "STOPPED" in html and "UNREACHABLE" in html and "STALE" in html
    assert "Process states below are from the last successful observation" in html
    assert "<script>bad</script>" not in html and "&lt;script&gt;bad&lt;/script&gt;" in html
    assert "https://airflow.example/dags/service/runs/manual__example" in html
    assert "https://airflow.example/dags/service/grid?tab=logs" in html
    assert "No Airflow links configured" in html
    assert "No observations yet" in render_viewer(None)


def test_airflow_config_can_build_collection_task():
    from airflow_config import Configuration

    cfg = instantiate(
        OmegaConf.create(
            {
                "_target_": "airflow_config.Configuration",
                "dags": {
                    "supervisor-observations": {
                        "dag_id": "supervisor-observations",
                        "tasks": {
                            "collect": {
                                "task_id": "collect",
                                "_target_": "airflow_pydantic.PythonTask",
                                "python_callable": "airflow_supervisor.collect_supervisor_status",
                                "op_kwargs": {
                                    "cfg": {
                                        "_target_": "airflow_supervisor.SupervisorViewerConfiguration",
                                        "instances": {
                                            "one": {"cfg": {"host": "host-a", "program": {}, "password": "demo"}}
                                        },
                                    }
                                },
                            }
                        },
                    }
                },
            }
        )
    )
    assert isinstance(cfg, Configuration)
    task = cfg.dags["supervisor-observations"].tasks["collect"]
    assert isinstance(task.op_kwargs["cfg"], SupervisorViewerConfiguration)
    arguments = task.model_dump(exclude_unset=True)["op_kwargs"]["cfg"]
    assert arguments["instances"]["one"]["cfg"]["password"] == "demo"
    password = SupervisorViewerConfiguration.model_validate(arguments).instances["one"].cfg.password
    assert password is not None and password.get_secret_value() == "demo"
    assert "collect_supervisor_status" in cfg.dags["supervisor-observations"].render()


def test_view_reads_selected_metadata_snapshot_without_contacting_instances(has_airflow, monkeypatch):
    now = datetime.now(UTC)
    snapshot = SupervisorSnapshot(
        collected_at=now,
        max_age=120,
        instances=[
            InstanceObservation(
                instance_id="selected",
                host="host-a",
                port=9001,
                attempted_at=now,
                observed_at=now,
                reachable=True,
                processes=[process(0)],
            )
        ],
    )
    monkeypatch.setenv("AIRFLOW_SUPERVISOR_SNAPSHOT_KEY", "selected-snapshot")
    with (
        patch(
            "airflow.models.Variable.get",
            side_effect=lambda key, **kwargs: {"selected-snapshot": snapshot.model_dump(mode="json")}.get(key),
        ) as read,
        patch("airflow_supervisor.airflow.viewer.SupervisorRemoteXMLRPCClient") as rpc,
    ):
        html = render_viewer(load_snapshot())
        assert "selected" in html and "STOPPED" in html
        read.assert_called_once_with("selected-snapshot", default_var=None, deserialize_json=True)
        monkeypatch.delenv("AIRFLOW_SUPERVISOR_SNAPSHOT_KEY")
        assert "No observations yet" in render_viewer(load_snapshot())
        rpc.assert_not_called()


def test_airflow_view_requires_authentication_and_has_no_write_routes(has_airflow):
    from airflow_pydantic.migration import _airflow_3

    from airflow_supervisor.ui import airflow as plugin

    with patch.object(plugin, "load_snapshot", return_value=None) as load:
        if _airflow_3():
            from fastapi.testclient import TestClient

            api_app = plugin.app
            client = TestClient(api_app)
            assert client.get("/").status_code == 401
            load.assert_not_called()
            dependency = api_app.router.dependencies[0].dependency
            assert dependency is not None
            api_app.dependency_overrides[dependency] = lambda: None
            try:
                response = client.get("/")
                assert client.post("/").status_code == 405
                assert client.post("/stop").status_code == 404
            finally:
                api_app.dependency_overrides.clear()
        else:
            from flask import Flask

            flask_app = Flask(__name__)
            flask_app.register_blueprint(plugin.bp)
            client = flask_app.test_client()
            manager = Mock(
                is_authorized_view=Mock(return_value=False),
                is_logged_in=Mock(return_value=False),
                get_url_login=Mock(return_value="/login"),
            )
            with patch("airflow.www.auth.get_auth_manager", return_value=manager):
                assert client.get("/airflow-supervisor/").status_code == 302
                load.assert_not_called()
                manager.is_authorized_view.return_value = True
                response = client.get("/airflow-supervisor/")
                assert client.post("/airflow-supervisor/").status_code == 405
                assert client.post("/airflow-supervisor/stop").status_code == 404
        assert response.status_code == 200
        assert response.headers["Cache-Control"] == "no-store"
        assert "No observations yet" in response.text
