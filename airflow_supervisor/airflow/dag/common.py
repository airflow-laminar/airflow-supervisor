from typing import TYPE_CHECKING, List, Optional, Union

from airflow.models.dag import DAG
from airflow.models.operator import Operator

from airflow_supervisor.config import SupervisorConfiguration


class SupervisorCommon(DAG):
    def __init__(self, supervisor_cfg: SupervisorConfiguration, **kwargs):
        super().__init__(**kwargs)
        self._supervisor_cfg = supervisor_cfg

        # tasks
        # configure supervisor
        #  | start supervisor
        #   | start programs
        #    | start watching programs
        #     | check programs
        #     | restart programs
        #      | stop watching programs
        #       | stop programs
        #        | stop supervisor
        #         | remove configuration
        self._configure_supervisor = None
        self._start_supervisor = None
        self._start_programs = None
        self._start_watch_programs = None
        self._check_programs = None
        self._restart_programs = None
        self._stop_watch_programs = None
        self._stop_programs = None
        self._stop_supervisor = None
        self._unconfigure_supervisor = None

    @property
    def configure_supervisor(self) -> Operator:
        return self._configure_supervisor

    @property
    def start_supervisor(self) -> Operator:
        return self._start_supervisor

    @property
    def start_programs(self) -> Operator:
        return self._start_programs

    @property
    def start_watch_programs(self) -> Operator:
        return self._start_watch_programs

    @property
    def check_programs(self) -> Operator:
        return self._check_programs

    @property
    def restart_programs(self) -> Operator:
        return self._restart_programs

    @property
    def stop_watch_programs(self) -> Operator:
        return self._stop_watch_programs

    @property
    def stop_programs(self) -> Operator:
        return self._stop_programs

    @property
    def stop_supervisor(self) -> Operator:
        return self._stop_supervisor

    @property
    def unconfigure_supervisor(self) -> Operator:
        return self._unconfigure_supervisor
