from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from http.client import HTTPConnection, HTTPSConnection
from xmlrpc.client import ServerProxy, Transport

from pydantic import BaseModel, Field, HttpUrl
from supervisor_pydantic import ProcessInfo, SupervisorRemoteXMLRPCClient

from airflow_supervisor.config.viewer import SupervisorViewerConfiguration

from .observability import _RPC_ERRORS
from .programs import _variable_get, _variable_set

__all__ = ("collect_supervisor_status",)


class InstanceObservation(BaseModel):
    instance_id: str
    host: str
    port: int
    attempted_at: datetime
    observed_at: datetime | None = None
    reachable: bool = False
    error: str | None = None
    processes: list[ProcessInfo] = Field(default_factory=list)
    run_url: HttpUrl | None = None
    log_url: HttpUrl | None = None


class SupervisorSnapshot(BaseModel):
    collected_at: datetime
    max_age: float = Field(gt=0)
    instances: list[InstanceObservation]


class _TimeoutTransport(Transport):
    def __init__(self, timeout, secure):
        super().__init__()
        self.timeout = timeout
        self.secure = secure

    def make_connection(self, host):
        hostname, self._extra_headers, _ = self.get_host_info(host)
        connection = HTTPSConnection if self.secure else HTTPConnection
        self._connection = (host, connection(hostname, timeout=self.timeout))
        return self._connection[1]


def _observe(instance_id, instance, timeout, previous):
    cfg = instance.cfg
    value = InstanceObservation(
        instance_id=instance_id,
        host=cfg.host,
        port=int(cfg.port.rsplit(":", 1)[-1]),
        attempted_at=datetime.now(UTC),
        run_url=instance.run_url,
        log_url=instance.log_url,
    )
    if previous and (previous.host, previous.port) == (value.host, value.port):
        value.observed_at, value.processes = previous.observed_at, previous.processes
    try:
        client = SupervisorRemoteXMLRPCClient(cfg)
        # The SDK has no transport option; keep its response parsing while bounding I/O.
        client._client = ServerProxy(
            client._rpcurl, transport=_TimeoutTransport(timeout, client._rpcurl.startswith("https:"))
        )
        with client._client:
            value.processes = client.getAllProcessInfo()
        value.observed_at = datetime.now(UTC)
        value.reachable = True
    except _RPC_ERRORS as error:
        # ProtocolError URLs can contain credentials. Store only the exception type.
        value.error = f"XML-RPC request failed ({type(error).__name__})"
    return value


def collect_supervisor_status(cfg):
    """Collect independently, retaining last successful data after a failed probe."""
    if isinstance(cfg, dict):
        cfg = SupervisorViewerConfiguration.model_validate(cfg)
    saved = _variable_get(cfg.variable_key)
    previous = SupervisorSnapshot.model_validate(saved) if saved else None
    by_id = {value.instance_id: value for value in previous.instances} if previous else {}
    with ThreadPoolExecutor(max_workers=min(4, len(cfg.instances))) as pool:
        futures = [
            pool.submit(_observe, name, instance, cfg.timeout, by_id.get(name))
            for name, instance in cfg.instances.items()
        ]
        values = [future.result() for future in futures]
    snapshot = SupervisorSnapshot(collected_at=datetime.now(UTC), max_age=cfg.max_age.total_seconds(), instances=values)
    _variable_set(cfg.variable_key, snapshot.model_dump(mode="json"))
    return {value.instance_id: value.reachable for value in values}
