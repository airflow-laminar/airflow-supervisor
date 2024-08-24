from logging import getLogger
from pathlib import Path
from time import sleep
from typer import Argument, Exit, Option, Typer
from typing import Callable, Optional, Union
from typing_extensions import Annotated

from ..client import SupervisorRemoteXMLRPCClient
from ..config import SupervisorAirflowConfiguration
from .common import SupervisorTaskStep

log = getLogger(__name__)

__all__ = (
    "write_supervisor_config",
    "start_supervisor",
    "start_programs",
    "check_programs",
    "stop_programs",
    "restart_programs",
    "stop_supervisor",
    "kill_supervisor",
    "remove_supervisor_config",
    "main",
)


def _check_exists(cfg: SupervisorAirflowConfiguration) -> bool:
    if cfg.working_dir.exists() and cfg.config_path.exists():
        # its probably already been written
        return True
    return False


def _check_same(cfg: SupervisorAirflowConfiguration) -> bool:
    if _check_exists(cfg) and cfg.config_path.read_text().strip() == cfg.to_cfg().strip():
        # same file contents
        return True
    elif not _check_exists(cfg):
        return True
    return False


def _check_running(cfg: SupervisorAirflowConfiguration) -> bool:
    if _check_same(cfg):
        return cfg.running()
    return False


def _wait_or_while(until: Callable, unless: Optional[Callable] = None, timeout: int = 5) -> bool:
    for _ in range(timeout):
        if until():
            return True
        if unless and unless():
            return False
        sleep(1)
    return False


def _raise_or_exit(val: bool, exit: bool):
    if exit:
        raise Exit(int(not val))
    return val


def _load_or_pass(cfg: Union[str, SupervisorAirflowConfiguration]) -> SupervisorAirflowConfiguration:
    if isinstance(cfg, Path):
        cfg = SupervisorAirflowConfiguration.model_validate_json(cfg.read_text())
    if isinstance(cfg, str):
        cfg = SupervisorAirflowConfiguration.model_validate_json(cfg)
    if not isinstance(cfg, SupervisorAirflowConfiguration):
        raise NotImplementedError
    return cfg


def write_supervisor_config(cfg_json: str, _exit: Annotated[bool, Argument(hidden=True)] = True):
    # NOTE: typer does not support union types
    cfg_obj = _load_or_pass(cfg_json)
    if not _check_same(cfg_obj):
        log.critical("Configs don't match")
    cfg_obj._write_self()
    return _raise_or_exit(True, _exit)


def start_supervisor(
    cfg: Annotated[
        Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)
    ] = Path("pydantic.json"),
    _exit: Annotated[bool, Argument(hidden=True)] = True,
):
    # NOTE: typer does not support union types
    cfg_obj = _load_or_pass(cfg)
    if not _check_same(cfg_obj):
        log.critical("Configs don't match")
    if _check_running(cfg_obj):
        return _raise_or_exit(True, _exit)
    cfg_obj.start(daemon=True)
    running = _wait_or_while(until=lambda: cfg_obj.running(), timeout=30)
    if not running:
        log.critical("Still not running 30s after start command!")
        return _raise_or_exit(False, _exit)
    return _raise_or_exit(True, _exit)


def start_programs(
    cfg: Annotated[
        Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)
    ] = Path("pydantic.json"),
    _exit: Annotated[bool, Argument(hidden=True)] = True,
):
    # NOTE: typer does not support union types
    cfg_obj = _load_or_pass(cfg)
    client = SupervisorRemoteXMLRPCClient(cfg=cfg_obj)

    ret = client.startAllProcesses()
    log.info(ret)

    _wait_or_while(
        until=lambda: all(_.running() for _ in client.getAllProcessInfo()),
        unless=lambda: any(_.stopped() for _ in client.getAllProcessInfo()),
        timeout=5,
    )
    all_ok = _wait_or_while(
        until=lambda: all(_.ok(ok_exitstatuses=cfg_obj.airflow.exitcodes) for _ in client.getAllProcessInfo()),
        unless=lambda: any(_.bad(ok_exitstatuses=cfg_obj.airflow.exitcodes) for _ in client.getAllProcessInfo()),
        timeout=10,
    )
    if not all_ok:
        for r in client.getAllProcessInfo():
            log.info(r.model_dump_json())
        log.warn("not all processes started")
        return _raise_or_exit(False, _exit)
    log.info("all processes started")
    return _raise_or_exit(True, _exit)


def check_programs(
    cfg: Annotated[
        Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)
    ] = Path("pydantic.json"),
    check_running: bool = False,
    check_done: bool = False,
    _exit: Annotated[bool, Argument(hidden=True)] = True,
):
    """Check if programs are in a good state.

    Args:
        cfg (Annotated[ Path, Option, optional): supervisor config
        check_running (bool, optional): if true, only return true if they're running
        check_done (bool, optional): if true, only return true if they're done (cleanly)
    """
    # NOTE: typer does not support union types
    cfg_obj = _load_or_pass(cfg)
    client = SupervisorRemoteXMLRPCClient(cfg=cfg_obj)

    ret = client.getAllProcessInfo()
    for r in ret:
        log.info(r.model_dump_json())

    ok = False
    if check_running:
        if all(p.running() for p in ret):
            log.info("all processes running")
            ok = True
        else:
            log.warn("not all processes running")
    elif check_done:
        if all(p.done(ok_exitstatuses=cfg_obj.airflow.exitcodes) for p in ret):
            log.info("all processes done")
            ok = True
        else:
            log.info("not all processes done")
    else:
        if all(p.ok(ok_exitstatuses=cfg_obj.airflow.exitcodes) for p in ret):
            log.info("all processes ok")
            ok = True
        else:
            log.info("not all processes ok")
    return _raise_or_exit(ok, _exit)


def stop_programs(
    cfg: Annotated[
        Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)
    ] = Path("pydantic.json"),
    _exit: Annotated[bool, Argument(hidden=True)] = True,
):
    # NOTE: typer does not support union types
    cfg_obj = _load_or_pass(cfg)
    client = SupervisorRemoteXMLRPCClient(cfg=cfg_obj)

    ret = client.stopAllProcesses()
    log.info(ret)

    all_stopped = _wait_or_while(until=lambda: all(_.stopped() for _ in client.getAllProcessInfo()), timeout=10)
    if not all_stopped:
        for r in client.getAllProcessInfo():
            log.info(r.model_dump_json())
        log.warn("not all processes stopped")
        return _raise_or_exit(False, _exit)
    log.info("all processes stopped")
    return _raise_or_exit(True, _exit)


def restart_programs(
    cfg: Annotated[
        Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)
    ] = Path("pydantic.json"),
    force: bool = False,
    _exit: Annotated[bool, Argument(hidden=True)] = True,
):
    if force:
        if not stop_programs(cfg, False):
            log.warn("could not stop programs")
            return _raise_or_exit(False, _exit)
    if not start_programs(cfg, False):
        log.warn("could not start programs")
        return _raise_or_exit(False, _exit)
    return _raise_or_exit(True, _exit)


def stop_supervisor(
    cfg: Annotated[
        Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)
    ] = Path("pydantic.json"),
    _exit: Annotated[bool, Argument(hidden=True)] = True,
):
    # NOTE: typer does not support union types
    cfg_obj = _load_or_pass(cfg)
    cfg_obj.stop()
    not_running = _wait_or_while(until=lambda: not cfg_obj.running(), timeout=30)
    if not not_running:
        log.critical("Still running 30s after stop command!")
        return _raise_or_exit(False, _exit)
    return _raise_or_exit(True, _exit)


def kill_supervisor(
    cfg: Annotated[
        Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)
    ] = Path("pydantic.json"),
    _exit: Annotated[bool, Argument(hidden=True)] = True,
):
    if not stop_programs(cfg, False):
        log.warn("could not stop programs")
    # NOTE: typer does not support union types
    cfg_obj = _load_or_pass(cfg)
    cfg_obj.kill()
    still_running = _wait_or_while(until=lambda: not cfg_obj.running(), timeout=30)
    if still_running:
        log.critical("Still running 30s after kill command!")
        return _raise_or_exit(False, _exit)
    return _raise_or_exit(True, _exit)


def remove_supervisor_config(
    cfg: Annotated[
        Path, Option(exists=True, file_okay=True, dir_okay=False, writable=False, readable=True, resolve_path=True)
    ] = Path("pydantic.json"),
    _exit: Annotated[bool, Argument(hidden=True)] = True,
):
    # NOTE: typer does not support union types
    cfg_obj = _load_or_pass(cfg)
    still_running = stop_supervisor(cfg_obj, _exit=False)
    if still_running:
        still_running = kill_supervisor(cfg_obj, _exit=False)

    if still_running:
        return _raise_or_exit(False, _exit)

    # TODO move to config
    sleep(5)

    # TODO make optional
    cfg_obj.rmdir()
    return _raise_or_exit(True, _exit)


def _add_to_typer(app, command: SupervisorTaskStep, foo):
    """Helper function to ensure correct command names"""
    app.command(command)(foo)


def main():
    app = Typer()
    _add_to_typer(app, "configure-supervisor", write_supervisor_config)
    _add_to_typer(app, "start-supervisor", start_supervisor)
    _add_to_typer(app, "start-programs", start_programs)
    _add_to_typer(app, "stop-programs", stop_programs)
    _add_to_typer(app, "check-programs", check_programs)
    _add_to_typer(app, "restart-programs", restart_programs)
    _add_to_typer(app, "stop-supervisor", stop_supervisor)
    _add_to_typer(app, "force-kill", kill_supervisor)
    _add_to_typer(app, "unconfigure-supervisor", remove_supervisor_config)
    app()
