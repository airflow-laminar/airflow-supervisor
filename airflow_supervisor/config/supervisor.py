import os
from datetime import datetime, timedelta, timezone
from hydra import compose, initialize_config_dir
from hydra.utils import instantiate
from logging import getLogger
from pathlib import Path
from pydantic import BaseModel, Field, PrivateAttr, model_validator
from shutil import rmtree
from signal import SIGKILL, SIGTERM
from subprocess import Popen
from tempfile import gettempdir
from typing import Dict, Optional

from ..exceptions import ConfigNotFoundError
from ..utils import _get_calling_dag
from .airflow import AirflowConfiguration
from .eventlistener import EventListenerConfiguration
from .fcgiprogram import FcgiProgramConfiguration
from .group import GroupConfiguration
from .include import IncludeConfiguration
from .inet_http_server import InetHttpServerConfiguration
from .program import ProgramConfiguration
from .rpcinterface import RpcInterfaceConfiguration
from .supervisorctl import SupervisorctlConfiguration
from .supervisord import SupervisordConfiguration
from .unix_http_server import UnixHttpServerConfiguration

__all__ = (
    "SupervisorConfiguration",
    "SupervisorAirflowConfiguration",
    "load_config",
    "load_airflow_config",
)

_log = getLogger(__name__)


class SupervisorConfiguration(BaseModel):
    def to_cfg(self) -> str:
        ret = ""
        if self.unix_http_server:
            ret += self.unix_http_server.to_cfg() + "\n"
        if self.inet_http_server:
            ret += self.inet_http_server.to_cfg() + "\n"
        if self.supervisord:
            ret += self.supervisord.to_cfg() + "\n"
        if self.supervisorctl:
            ret += self.supervisorctl.to_cfg() + "\n"
        if self.include:
            ret += self.include.to_cfg() + "\n"
        for k, v in self.program.items():
            ret += v.to_cfg(key=k) + "\n"
        for k, v in (self.group or {}).items():
            ret += v.to_cfg(key=k) + "\n"
        for k, v in (self.fcgiprogram or {}).items():
            ret += v.to_cfg(key=k) + "\n"
        for k, v in (self.eventlistener or {}).items():
            ret += v.to_cfg(key=k) + "\n"
        for k, v in (self.rpcinterface or {}).items():
            ret += v.to_cfg(key=k) + "\n"
        return ret

    # supervisor setup
    unix_http_server: Optional[UnixHttpServerConfiguration] = Field(default=None)
    inet_http_server: Optional[InetHttpServerConfiguration] = Field(default=None)
    supervisord: SupervisordConfiguration = Field(default=SupervisordConfiguration())
    supervisorctl: SupervisorctlConfiguration = Field(default=SupervisorctlConfiguration())
    include: Optional[IncludeConfiguration] = Field(default=None)

    program: Dict[str, ProgramConfiguration]
    group: Optional[Dict[str, GroupConfiguration]] = Field(default=None)

    fcgiprogram: Optional[Dict[str, FcgiProgramConfiguration]] = Field(default=None)
    eventlistener: Optional[Dict[str, EventListenerConfiguration]] = Field(default=None)
    rpcinterface: Optional[Dict[str, RpcInterfaceConfiguration]] = Field(default=None)

    # other configuration
    config_path: Optional[Path] = Field(default="", description="Path to supervisor configuration file")
    working_dir: Optional[Path] = Field(default="", description="Path to supervisor working directory")

    @model_validator(mode="after")
    def _setup_config_and_working_dir(self):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        tempdir = Path(gettempdir()).resolve()

        if self.working_dir == "":
            if self.supervisord.directory:
                # use this as the dir
                self.working_dir = self.supervisord.directory
            else:
                self.working_dir = tempdir / f"supervisor-{now}"
                self.supervisord.directory = self.working_dir
            using_default_working_dir = True
        else:
            using_default_working_dir = False

        # force pidfile to be in working dir if not otherwise set
        if not self.supervisord.pidfile:
            self.supervisord.pidfile = self.working_dir / "supervisord.pid"

        # force logfile to be in working dir if not otherwise set
        if not self.supervisord.logfile:
            self.supervisord.logfile = self.working_dir / "supervisord.log"

        if self.config_path == "":
            if using_default_working_dir:
                self.config_path = self.working_dir / "supervisor.cfg"
            else:
                self.config_path = self.working_dir / f"supervisor-{now}.cfg"

        for name, program_config in self.program.items():
            if program_config.directory is None:
                program_config.directory = self.working_dir / name
        return self

    @classmethod
    def _find_parent_config_folder(
        cls, config_dir: str = "config", config_name: str = "", *, basepath: str = "", _offset: int = 2
    ):
        if basepath:
            if basepath.endswith((".py", ".cfg", ".yml", ".yaml")):
                calling_dag = Path(basepath)
            else:
                calling_dag = Path(basepath) / "dummy.py"
        else:
            calling_dag = Path(_get_calling_dag(offset=_offset))
        folder = calling_dag.parent.resolve()
        exists = (
            (folder / config_dir).exists()
            if not config_name
            else (
                (folder / config_dir / f"{config_name}.yml").exists()
                or (folder / config_dir / f"{config_name}.yaml").exists()
            )
        )
        while not exists:
            folder = folder.parent
            if str(folder) == os.path.abspath(os.sep):
                raise ConfigNotFoundError(config_dir=config_dir, dagfile=calling_dag)
            exists = (
                (folder / config_dir).exists()
                if not config_name
                else (
                    (folder / config_dir / f"{config_name}.yml").exists()
                    or (folder / config_dir / f"{config_name}.yaml").exists()
                )
            )

        config_dir = (folder / config_dir).resolve()
        if not config_name:
            return folder.resolve(), config_dir, ""
        elif (folder / config_dir / f"{config_name}.yml").exists():
            return folder.resolve(), config_dir, (folder / config_dir / f"{config_name}.yml").resolve()
        return folder.resolve(), config_dir, (folder / config_dir / f"{config_name}.yaml").resolve()

    @classmethod
    def load(
        cls: "SupervisorConfiguration",
        config_dir: str = "config",
        config_name: str = "",
        overrides: Optional[list[str]] = None,
        *,
        basepath: str = "",
        _offset: int = 3,
    ) -> "SupervisorConfiguration":
        overrides = overrides or []

        with initialize_config_dir(config_dir=str(Path(__file__).resolve().parent / "hydra"), version_base=None):
            if config_dir:
                hydra_folder, config_dir, _ = cls._find_parent_config_folder(
                    config_dir=config_dir, config_name=config_name, basepath=basepath, _offset=_offset
                )

                cfg = compose(config_name="base", overrides=[], return_hydra_config=True)
                searchpaths = cfg["hydra"]["searchpath"]
                searchpaths.extend([hydra_folder, config_dir])
                if config_name:
                    overrides = [
                        f"+config={config_name}",
                        *overrides.copy(),
                        f"hydra.searchpath=[{','.join(searchpaths)}]",
                    ]
                else:
                    overrides = [*overrides.copy(), f"hydra.searchpath=[{','.join(searchpaths)}]"]

            cfg = compose(config_name="base", overrides=overrides)
            config = instantiate(cfg)

            if not isinstance(config, cls):
                if issubclass(cls, type(config)):
                    config = config.model_dump()
                config = cls(**config)
            return config

    def write(self):
        _log.info(f"Making working dir: {self.working_dir}")
        self.working_dir.mkdir(parents=True, exist_ok=True)
        for program_name, program_config in self.program.items():
            if program_config.directory:
                _log.info(f"Making program dir ({program_name}): {program_config.directory}")
                program_config.directory.mkdir(exist_ok=True)
        _log.info(f"Writing config file: {self.config_path}")
        self.config_path.write_text(self.to_cfg())

    def rmdir(self):
        if not self.running():
            _log.info(f"Removing working dir: {self.working_dir}")
            rmtree(self.working_dir)

    def start(self, daemon: bool = False):
        _log.info(f"Starting supervisord: {self.config_path}")
        if not self.running():
            if daemon is False:
                Popen(f"supervisord -n -c {str(self.config_path)}", shell=True)
                return
            Popen(f"supervisord -c {str(self.config_path)}", close_fds=True, shell=True)

    def running(self):
        # grab the pidfile, find the process with the pid, and kill
        _log.info(f"Checking supervisord: {self.supervisord.pidfile}")
        if not self.supervisord.pidfile.exists():
            return False
        try:
            os.kill(int(self.supervisord.pidfile.read_text()), 0)
        except OSError:
            return False
        return True

    def stop(self):
        if self.running():
            # grab the pidfile, find the process with the pid, and kill with SIGTERM
            _log.info(f"Stopping supervisord: {self.supervisord.pidfile}")
            os.kill(int(self.supervisord.pidfile.read_text()), SIGTERM)

    def kill(self):
        if self.running():
            # grab the pidfile, find the process with the pid, and kill with SIGKILL
            _log.info(f"Killing supervisord: {self.supervisord.pidfile}")
            os.kill(int(self.supervisord.pidfile.read_text()), SIGKILL)


class SupervisorAirflowConfiguration(SupervisorConfiguration):
    airflow: AirflowConfiguration = Field(
        default_factory=AirflowConfiguration, description="Required configurations for Airflow integration"
    )
    check_interval: timedelta = Field(
        default=timedelta(seconds=5), description="Interval between supervisor program status checks"
    )
    check_timeout: timedelta = Field(
        default=timedelta(hours=8), description="Timeout to wait for supervisor program status checks"
    )

    _pydantic_path: Path = PrivateAttr(default="pydantic.json")

    def _write_self(self):
        # TODO make config driven
        self.write()
        _log.info(f"Writing model json: {self._pydantic_path}")
        Path(self._pydantic_path).write_text(self.model_dump_json())

    @model_validator(mode="after")
    def _setup_airflow_defaults(self):
        """Method to overload configuration with values needed for the setup
        of airflow tasks that we construct"""
        # inet_http_server
        if not self.inet_http_server:
            self.inet_http_server = InetHttpServerConfiguration()

        self.inet_http_server.port = self.airflow.port
        self.inet_http_server.username = self.airflow.username
        self.inet_http_server.password = self.airflow.password

        self.supervisorctl.serverurl = (
            f"{self.airflow.protocol}://{self.airflow.host}:{self.airflow.port.split(':')[-1]}/"
        )

        # rpcinterface
        if not self.rpcinterface:
            self.rpcinterface = {"supervisor": RpcInterfaceConfiguration()}
        self.rpcinterface["supervisor"].rpcinterface_factory = self.airflow.rpcinterface_factory

        # supervisord
        self.supervisord.nodaemon = True
        self.supervisord.identifier = "supervisor"

        # programs
        for config in self.program.values():
            config.autostart = False
            config.autorestart = False
            config.startsecs = self.airflow.startsecs
            config.startretries = self.airflow.startretries
            config.exitcodes = self.airflow.exitcodes
            config.stopsignal = self.airflow.stopsignal
            config.stopwaitsecs = self.airflow.stopwaitsecs

        # other
        if str(self.working_dir) not in str(self._pydantic_path):
            self._pydantic_path = self.working_dir / "pydantic.json"
        return self


load_config = SupervisorConfiguration.load
load_airflow_config = SupervisorAirflowConfiguration.load
