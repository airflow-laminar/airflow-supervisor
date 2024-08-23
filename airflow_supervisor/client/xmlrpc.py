from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Dict, List
from xmlrpc.client import Fault, ServerProxy

from ..config import SupervisorAirflowConfiguration

__all__ = ("SupervisorRemoteXMLRPCClient", "ProcessState", "SupervisorState", "SupervisorMethodResult", "ProcessInfo")


class ProcessState(Enum):
    STOPPED = 0
    STARTING = 10
    RUNNING = 20
    BACKOFF = 30
    STOPPING = 40
    EXITED = 100
    FATAL = 200
    UNKNOWN = 1000

    @classmethod
    def _missing_(cls, code):
        if isinstance(code, str):
            return getattr(cls, code)
        if code not in (0, 10, 20, 30, 40, 100, 200):
            return super().__init__(1000)
        raise ValueError(code)


class SupervisorState(Enum):
    FATAL = 2
    RUNNING = 1
    RESTARTING = 0
    SHUTDOWN = -1

    @classmethod
    def _missing_(cls, code):
        if isinstance(code, str):
            return getattr(cls, code)
        raise ValueError(code)


class SupervisorMethodResult(Enum):
    # duplicated from https://github.com/Supervisor/supervisor/blob/29eeb9dd55c55da2e83c5497d01f3a859998ecf9/supervisor/xmlrpc.py
    UNKNOWN_METHOD = 1
    INCORRECT_PARAMETERS = 2
    BAD_ARGUMENTS = 3
    SIGNATURE_UNSUPPORTED = 4
    SHUTDOWN_STATE = 6
    BAD_NAME = 10
    BAD_SIGNAL = 11
    NO_FILE = 20
    NOT_EXECUTABLE = 21
    FAILED = 30
    ABNORMAL_TERMINATION = 40
    SPAWN_ERROR = 50
    ALREADY_STARTED = 60
    NOT_RUNNING = 70
    SUCCESS = 80
    ALREADY_ADDED = 90
    STILL_RUNNING = 91
    CANT_REREAD = 92


class ProcessInfo(BaseModel):
    name: str
    group: str
    state: ProcessState
    description: str
    start: datetime
    stop: datetime
    now: datetime
    spawner: str = ""
    exitstatus: int
    logfile: str
    stdout_logfile: str
    stderr_logfile: str
    pid: int

    def running(self):
        return self.state in (ProcessState.RUNNING, ProcessState.STOPPING)

    def stopped(self):
        return self.state in (ProcessState.STOPPED, ProcessState.EXITED, ProcessState.FATAL)

    def done(self, ok_exitstatuses=None):
        ok_exitstatuses = ok_exitstatuses or (0,)
        return self.state in (ProcessState.STOPPED,) or (
            self.state == ProcessState.EXITED and self.exitstatus in ok_exitstatuses
        )

    def ok(self, ok_exitstatuses=None):
        ok_exitstatuses = ok_exitstatuses or (0,)
        return self.state in (
            # ProcessState.STARTING,
            ProcessState.RUNNING,
            ProcessState.STOPPING,
            ProcessState.STOPPED,
        ) or (self.state == ProcessState.EXITED and self.exitstatus in ok_exitstatuses)

    def bad(self, ok_exitstatuses=None):
        ok_exitstatuses = ok_exitstatuses or (0,)
        return self.state in (ProcessState.FATAL, ProcessState.UNKNOWN) or (
            self.state == ProcessState.EXITED and self.exitstatus not in ok_exitstatuses
        )


class SupervisorRemoteXMLRPCClient(object):
    """A light wrapper over the supervisor xmlrpc api: http://supervisord.org/api.html"""

    def __init__(self, cfg: SupervisorAirflowConfiguration):
        self._cfg = cfg
        self._host = cfg.airflow.host
        self._port = int(cfg.airflow.port.split(":")[-1])
        self._protocol = cfg.airflow.protocol
        self._rpcpath = "/" + cfg.airflow.rpcpath if not cfg.airflow.rpcpath.startswith("/") else cfg.airflow.rpcpath

        if cfg.airflow.port == 80:
            # force http
            self._rpcurl = f"http://{self._host}{self._rpcpath}"
        elif cfg.airflow.port == 443:
            # force https
            self._rpcurl = f"https://{self._host}{self._rpcpath}"
        else:
            self._rpcurl = f"{self._protocol}://{self._host}:{self._port}{self._rpcpath}"
        self._client = ServerProxy(self._rpcurl)

    #######################
    # supervisord methods #
    #######################
    def getAllProcessInfo(self) -> List[ProcessInfo]:
        return [ProcessInfo(**_) for _ in self._client.supervisor.getAllProcessInfo()]

    def getState(self):
        return SupervisorState(self._client.supervisor.getState()["statecode"])

    # def readLog(self):
    #     return self._client.supervisor.readLog(0, 0)

    def restart(self):
        return self._client.supervisor.restart()

    def shutdown(self):
        return self._client.supervisor.shutdown()

    ###################
    # process methods #
    ###################
    def getProcessInfo(self, name: str):
        if name not in self._cfg.program:
            raise RuntimeError(f"Unknown process: {name}")
        return ProcessInfo(**self._client.supervisor.getProcessInfo(name))

    def readProcessLog(self, name: str):
        if name not in self._cfg.program:
            raise RuntimeError(f"Unknown process: {name}")
        return self._client.supervisor.readProcessLog(name, 0, 0)

    def readProcessStderrLog(self, name: str):
        if name not in self._cfg.program:
            raise RuntimeError(f"Unknown process: {name}")

        return self._client.supervisor.readProcessStderrLog()

    def readProcessStdoutLog(self, name: str):
        return self._client.supervisor.readProcessStdoutLog()

    def startAllProcesses(self) -> Dict[str, ProcessInfo]:
        # start all
        self._client.supervisor.startAllProcesses()
        return {name: self.getProcessInfo(name) for name in self._cfg.program}

    def startProcess(self, name: str) -> ProcessInfo:
        if name not in self._cfg.program:
            raise RuntimeError(f"Unknown process: {name}")
        try:
            if self._client.supervisor.startProcess(name):
                return self.getProcessInfo(name)
        except Fault as f:
            if f.faultCode == SupervisorMethodResult.ALREADY_STARTED.value:
                return self.getProcessInfo(name)
            if f.faultCode == SupervisorMethodResult.SPAWN_ERROR.value:
                return self.getProcessInfo(name)
            raise f
        return self.getProcessInfo(name)

    def stopAllProcesses(self) -> Dict[str, ProcessInfo]:
        # start all
        self._client.supervisor.stopAllProcesses()
        return {name: self.getProcessInfo(name) for name in self._cfg.program}

    def stopProcess(self, name: str) -> ProcessInfo:
        if name not in self._cfg.program:
            raise RuntimeError(f"Unknown process: {name}")
        try:
            if self._client.supervisor.stopProcess(name):
                return self.getProcessInfo(name)
        except Fault as f:
            if f.faultCode == SupervisorMethodResult.NOT_RUNNING.value:
                return self.getProcessInfo(name)
            raise f
        return self.getProcessInfo(name)

    # def reloadConfig(self):
    #     return self._client.supervisor.reloadConfig()

    # def signalAllProcesses(self, signal):
    #     return self._client.supervisor.signalAllProcesses()

    def signalProcess(self, name: str, signal):
        if name not in self._cfg.program:
            raise RuntimeError(f"Unknown process: {name}")
        return self._client.supervisor.signalProcess()
