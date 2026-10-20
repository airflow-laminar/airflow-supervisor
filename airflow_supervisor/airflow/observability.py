from logging import getLogger
from xmlrpc.client import Fault, ProtocolError

from supervisor_pydantic import ProcessState, SupervisorRemoteXMLRPCClient

from airflow_supervisor.config.supervisor import SupervisorAirflowConfiguration

__all__ = ("check_supervisor_health",)

_log = getLogger(__name__)
_LOG_OFFSETS = "supervisor_log_offsets"
_STATUS = "supervisor_process_status"
_RPC_ERRORS = (OSError, Fault, ProtocolError, ValueError, RuntimeError)


def _status(infos):
    return [
        {
            "name": info.name,
            "group": info.group,
            "state": info.state.name,
            "exitstatus": info.exitstatus,
            "spawnerr": info.spawnerr,
            "pid": info.pid,
        }
        for info in infos
    ]


def _publish_status(infos, context, exitcodes=None, failed=False):
    value = _status(infos)
    ti = context.get("task_instance") or context.get("ti")
    if ti is not None:
        ti.xcom_push(key=_STATUS, value=value)
        if failed or any(info.bad(exitcodes) for info in infos):
            ti.xcom_push(key="supervisor_failure", value=value)
    return value


def _failure_details(infos):
    return "; ".join(
        f"{info.group}:{info.name} state={info.state.name} exitstatus={info.exitstatus} spawnerr={info.spawnerr or '-'}"
        for info in infos
    )


class _LogForwarder:
    def __init__(self, cfg, client, task_ids=()):
        self.cfg = cfg
        self.client = client
        self.task_ids = task_ids
        self.offsets = {}
        self.pending = {}
        self.warned = set()
        self.loaded = False

    def _load(self, context):
        if self.loaded:
            return
        self.loaded = True
        ti = context.get("task_instance") or context.get("ti")
        if ti is None:
            return
        ids = [ti.task_id, *self.task_ids]
        values = ti.xcom_pull(key=_LOG_OFFSETS, task_ids=ids, include_prior_dates=True)
        if isinstance(values, dict):
            values = [values]
        current_run = context.get("run_id") or ti.run_id
        for value in values or []:
            if isinstance(value, dict) and (not self.task_ids or value.get("run_id") == current_run):
                self.offsets = value.get("offsets", {}).copy()
                break

    def _save(self, context):
        ti = context.get("task_instance") or context.get("ti")
        if ti is not None:
            offsets = {
                key: offset - len(self.pending.get(key, "").encode("utf-8")) for key, offset in self.offsets.items()
            }
            ti.xcom_push(key=_LOG_OFFSETS, value={"run_id": context.get("run_id") or ti.run_id, "offsets": offsets})

    def baseline(self, infos, context):
        if not self.cfg.forward_logs:
            return
        self._load(context)
        for info in infos:
            name = f"{info.group}:{info.name}"
            for channel in ("stdout", "stderr"):
                key = f"{name}:{channel}"
                try:
                    self.offsets[key] = self.client.getProcessLogSize(name, channel)
                    self.pending.pop(key, None)
                except _RPC_ERRORS as error:
                    self._warn(key, error)
        self._save(context)

    def _warn(self, key, error):
        if key not in self.warned:
            _log.warning("Cannot forward supervisor log %s: %s", key, error)
            self.warned.add(key)

    def forward(self, infos, context, flush=False):
        if not self.cfg.forward_logs:
            return
        self._load(context)
        for info in infos:
            name = f"{info.group}:{info.name}"
            for channel in ("stdout", "stderr"):
                key = f"{name}:{channel}"
                for _ in range(16 if flush else 1):
                    try:
                        chunk = self.client.readProcessLogChunk(
                            name, channel, self.offsets.get(key, 0), self.cfg.log_chunk_size
                        )
                    except _RPC_ERRORS as error:
                        self._warn(key, error)
                        break
                    if chunk.truncated:
                        _log.warning("Supervisor log %s was truncated or rotated; resetting cursor", key)
                        self.pending.pop(key, None)
                    self.offsets[key] = chunk.offset
                    text = self.pending.get(key, "") + chunk.text
                    lines = text.split("\n")
                    self.pending[key] = lines.pop()
                    for line in lines:
                        _log.info("[supervisor %s %s] %s", name, channel, line.rstrip("\r"))
                    if len(self.pending[key].encode("utf-8")) >= self.cfg.log_chunk_size:
                        _log.info("[supervisor %s %s] %s", name, channel, self.pending.pop(key))
                    if not chunk.text:
                        break
                else:
                    if flush:
                        _log.warning("Supervisor log %s reached the final drain limit", key)
                if flush and self.pending.get(key):
                    _log.info("[supervisor %s %s] %s", name, channel, self.pending.pop(key))
        self._save(context)


def check_supervisor_health(cfg, require_running=True, supervisor_client=None, **context):
    """Check an existing instance without starting, stopping, or reconfiguring it."""
    from airflow.exceptions import AirflowException

    if isinstance(cfg, dict):
        cfg = SupervisorAirflowConfiguration.model_validate(cfg)
    client = supervisor_client or SupervisorRemoteXMLRPCClient(cfg)
    try:
        infos = client.getProgramProcessInfo()
    except _RPC_ERRORS as error:
        raise AirflowException(f"Supervisor health check failed: {error}") from error
    _LogForwarder(cfg, client).forward(infos, context, flush=True)
    healthy = bool(infos) and all(
        info.state in (ProcessState.STARTING, ProcessState.RUNNING) if require_running else info.ok(cfg.exitcodes)
        for info in infos
    )
    summary = _publish_status(infos, context, cfg.exitcodes, failed=not healthy)
    if not healthy:
        raise AirflowException(f"Supervisor is unhealthy: {_failure_details(infos) or 'no workload processes'}")
    return {"host": cfg.host, "healthy": True, "processes": summary}
