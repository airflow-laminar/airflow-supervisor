import signal
import sys

from supervisor_pydantic import SupervisorRemoteXMLRPCClient
from supervisor_pydantic.convenience import start_supervisor, write_supervisor_config

from airflow_supervisor import SupervisorAirflowConfiguration

clients = []


def stop(signum, frame):
    raise SystemExit(0)


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    for port in map(int, sys.argv[1:]):
        cfg = SupervisorAirflowConfiguration(
            working_dir=f"/tmp/supervisor-{port}",
            port=f"*:{port}",
            username="demo",
            password="demo",
            command_timeout=5,
            startsecs=0,
            program={"worker": {"command": "python -u /demo/workload.py"}},
            eventlistener={
                "multivisor-rpc": {
                    "command": f"multivisor-rpc --bind 0.0.0.0:{port + 1}",
                    "events": ["PROCESS_STATE", "SUPERVISOR_STATE_CHANGE"],
                    "startsecs": 0,
                    "environment": {"SUPERVISOR_USERNAME": "demo", "SUPERVISOR_PASSWORD": "demo"},
                }
            },
        )
        assert write_supervisor_config(cfg.model_dump_json(exclude_unset=True), _exit=False)
        assert start_supervisor(cfg, _exit=False)
        client = SupervisorRemoteXMLRPCClient(cfg)
        clients.append(client)
        client.startAllProcesses()
    print("Supervisor instances ready", flush=True)
    signal.pause()
finally:
    for client in clients:
        client.shutdown()
