from logging import getLogger
from pathlib import Path
from time import sleep
from typer import Exit, Option, Typer
from typing_extensions import Annotated

from ..client import SupervisorRemoteXMLRPCClient
from ..config import SupervisorAirflowConfiguration
from .dag.setup import _SupervisorTaskStep

log = getLogger(__name__)


def _check_exists(cfg: SupervisorAirflowConfiguration) -> bool:
    if cfg.working_dir.exists() and cfg.config_path.exists():
        # its probably already been written
        return True
    return False


def _check_same(cfg: SupervisorAirflowConfiguration) -> bool:
    if _check_exists(cfg) and cfg.config_path.read_text().strip() == cfg.to_cfg().strip():
        # same file contents
        return True
    return False


def _check_running(cfg: SupervisorAirflowConfiguration) -> bool:
    if _check_same(cfg):
        return cfg.running()
    return False


def _wait_or_while(until, timeout: int = 5) -> bool:
    for _ in range(timeout):
        if until():
            return True
        sleep(1)
    return False


def write_supervisor_config(cfg_json: str):
    cfg_obj = SupervisorAirflowConfiguration.model_validate_json(cfg_json)
    if not _check_same(cfg_obj):
        log.critical("Configs don't match")
    cfg_obj.write()
    return Exit(0)


def start_supervisor(
    cfg: Annotated[Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)], exit: bool = True
):
    cfg_obj = SupervisorAirflowConfiguration.model_validate_json(cfg.read_text())
    if not _check_same(cfg_obj):
        log.critical("Configs don't match")
    if _check_running(cfg_obj):
        return
    cfg_obj.start(daemon=True)
    still_not_running = _wait_or_while(until=lambda: cfg_obj.running(), timeout=30)
    if still_not_running:
        log.critical("Still not running 30s after start command!")
        return Exit(1) if exit else False
    return Exit(0) if exit else True


def start_programs(cfg: Annotated[Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)]):
    cfg_obj = SupervisorAirflowConfiguration.model_validate_json(cfg.read_text())
    client = SupervisorRemoteXMLRPCClient(cfg=cfg_obj)
    # TODO
    ret = client.startAllProcesses()
    log.info(ret)
    return Exit(0)


def check_programs(cfg: Annotated[Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)]):
    cfg_obj = SupervisorAirflowConfiguration.model_validate_json(cfg.read_text())
    client = SupervisorRemoteXMLRPCClient(cfg=cfg_obj)
    # TODO
    ret = client.getAllProcessInfo()
    log.info(ret)
    return Exit(0)


def restart_programs(cfg: Annotated[Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)]):
    cfg_obj = SupervisorAirflowConfiguration.model_validate_json(cfg.read_text())
    client = SupervisorRemoteXMLRPCClient(cfg=cfg_obj)
    # TODO
    ret1 = client.stopAllProcesses()
    log.info(ret1)
    ret2 = client.startAllProcesses()
    log.info(ret2)
    return Exit(0)


def stop_supervisor(
    cfg: Annotated[Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)], exit: bool = True
):
    cfg_obj = SupervisorAirflowConfiguration.model_validate_json(cfg.read_text())
    cfg_obj.stop()
    still_running = _wait_or_while(until=lambda: not cfg_obj.running(), timeout=30)
    if still_running:
        log.critical("Still running 30s after stop command!")
        return Exit(1) if exit else False
    return Exit(0) if exit else True


def kill_supervisor(
    cfg: Annotated[Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)], exit: bool = False
):
    cfg_obj = SupervisorAirflowConfiguration.model_validate_json(cfg.read_text())
    cfg_obj.kill()
    still_running = _wait_or_while(until=lambda: not cfg_obj.running(), timeout=30)
    if still_running:
        log.critical("Still running 30s after kill command!")
        return Exit(1) if exit else False
    return Exit(0) if exit else True


def remove_supervisor_config(
    cfg: Annotated[Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)],
):
    cfg_obj = SupervisorAirflowConfiguration.model_validate_json(cfg.read_text())
    still_running = stop_supervisor(cfg_obj, exit=False)
    if still_running:
        still_running = kill_supervisor(cfg_obj, exit=False)

    if still_running:
        Exit(1)

    # TODO move to config
    sleep(5)

    # TODO make optional
    cfg_obj.rmdir()
    return Exit(0)


def _add_to_typer(app, command: _SupervisorTaskStep, foo):
    """Helper function to ensure correct command names"""
    app.command(command)(foo)


def main():
    app = Typer()
    _add_to_typer(app, "configure-supervisor", write_supervisor_config)
    _add_to_typer(app, "start-supervisor", start_supervisor)
    _add_to_typer(app, "start-programs", start_programs)
    _add_to_typer(app, "check-programs", check_programs)
    _add_to_typer(app, "restart-programs", restart_programs)
    _add_to_typer(app, "stop-supervisor", stop_supervisor)
    _add_to_typer(app, "force-kill", kill_supervisor)
    _add_to_typer(app, "unconfigure-supervisor", remove_supervisor_config)
    app()
