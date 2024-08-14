import os
from datetime import UTC, datetime
from pathlib import Path
from tempfile import gettempdir
from typing import Dict, Optional

from hydra import compose, initialize_config_dir
from hydra.utils import instantiate
from pydantic import BaseModel, Field
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
from ..exceptions import ConfigNotFoundError
from ..utils import _get_calling_dag


__all__ = (
    "SupervisorConfiguration",
    "load_config",
)


def _generate_supervisor_config_path() -> Path:
    return Path(gettempdir()).resolve() / f"supervisor-{datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S')}"


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
    supervisord: Optional[SupervisordConfiguration] = Field(default=None)
    supervisorctl: Optional[SupervisorctlConfiguration] = Field(default=None)
    include: Optional[IncludeConfiguration] = Field(default=None)

    program: Dict[str, ProgramConfiguration]
    group: Optional[Dict[str, GroupConfiguration]] = Field(default=None)

    fcgiprogram: Optional[Dict[str, FcgiProgramConfiguration]] = Field(default=None)
    eventlistener: Optional[Dict[str, EventListenerConfiguration]] = Field(default=None)
    rpcinterface: Optional[Dict[str, RpcInterfaceConfiguration]] = Field(default=None)

    # other configuration
    path: Optional[Path] = Field(default_factory=_generate_supervisor_config_path, description="Path to supervisor configuration")

    @staticmethod
    def _find_parent_config_folder(config_dir: str = "config", config_name: str = "", *, basepath: str = "", _offset: int = 2):
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
            else ((folder / config_dir / f"{config_name}.yml").exists() or (folder / config_dir / f"{config_name}.yaml").exists())
        )
        while not exists:
            folder = folder.parent
            if str(folder) == os.path.abspath(os.sep):
                raise ConfigNotFoundError(config_dir=config_dir, dagfile=calling_dag)
            exists = (
                (folder / config_dir).exists()
                if not config_name
                else ((folder / config_dir / f"{config_name}.yml").exists() or (folder / config_dir / f"{config_name}.yaml").exists())
            )

        config_dir = (folder / config_dir).resolve()
        if not config_name:
            return folder.resolve(), config_dir, ""
        elif (folder / config_dir / f"{config_name}.yml").exists():
            return folder.resolve(), config_dir, (folder / config_dir / f"{config_name}.yml").resolve()
        return folder.resolve(), config_dir, (folder / config_dir / f"{config_name}.yaml").resolve()

    @staticmethod
    def load(
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
                hydra_folder, config_dir, _ = SupervisorConfiguration._find_parent_config_folder(
                    config_dir=config_dir, config_name=config_name, basepath=basepath, _offset=_offset
                )

                cfg = compose(config_name="base", overrides=[], return_hydra_config=True)
                searchpaths = cfg["hydra"]["searchpath"]
                searchpaths.extend([hydra_folder, config_dir])
                if config_name:
                    overrides = [f"+config={config_name}", *overrides.copy(), f"hydra.searchpath=[{','.join(searchpaths)}]"]
                else:
                    overrides = [*overrides.copy(), f"hydra.searchpath=[{','.join(searchpaths)}]"]

            cfg = compose(config_name="base", overrides=overrides)
            config = instantiate(cfg)

            if not isinstance(config, SupervisorConfiguration):
                config = SupervisorConfiguration(**config)
            return config


load_config = SupervisorConfiguration.load
