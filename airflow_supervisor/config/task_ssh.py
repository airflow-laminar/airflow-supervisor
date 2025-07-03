from types import FunctionType, MethodType
from typing import Any, Optional, Type, Union

from airflow_pydantic import CallablePath, Host, HostQuery, ImportPath, Port, PortQuery, Task, TaskArgs, get_import_path
from pydantic import Field, TypeAdapter, field_validator, model_validator

from .supervisor_ssh import SupervisorSSHAirflowConfiguration

__all__ = (
    "SupervisorSSHOperatorArgs",
    "SupervisorSSHTaskArgs",
    "SupervisorSSHOperator",
    "SupervisorSSHTask",
)


class SupervisorSSHTaskArgs(TaskArgs, extra="allow"):
    cfg: SupervisorSSHAirflowConfiguration
    host: Optional[Union[Host, HostQuery, CallablePath]] = Field(
        default=None,
        description="The host to connect to for SSH, if not otherwise provided in configs",
    )
    host_foo: Optional[CallablePath] = Field(default=None, exclude=True)
    port: Optional[Union[Port, PortQuery, CallablePath]] = Field(
        default=None,
        description="The port to user for Supervisor, if not otherwise provided in configs",
    )
    port_foo: Optional[CallablePath] = Field(default=None, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _extract_host(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "host" in data:
                host = data["host"]
                if isinstance(host, (HostQuery, Host)):
                    if isinstance(host, HostQuery):
                        # Ensure that the BalancerHostQueryConfiguration is of kind 'select'
                        if not host.kind == "select":
                            raise ValueError("BalancerHostQueryConfiguration must be of kind 'select'")
                        data["host"] = host.execute()

                if isinstance(host, str):
                    # If host is a string, we assume it's an import path
                    data["host"] = get_import_path(host)

                    try:
                        data["host"] = data["host"]()
                    except Exception:
                        # Skip, might only run in situ
                        data["host"] = None

                if isinstance(host, (FunctionType, MethodType)):
                    # If host is a callable, we need to call it to get the Host instance
                    data["host_foo"] = get_import_path(host)

                    try:
                        data["host"] = data["host_foo"]()
                    except Exception:
                        # Skip, might only run in situ
                        data["host"] = None
            if "port" in data:
                port = data["port"]
                if isinstance(port, (PortQuery, Port)):
                    if isinstance(port, PortQuery):
                        # Ensure that the BalancerPortQueryConfiguration is of kind 'select'
                        if not port.kind == "select":
                            raise ValueError("BalancerPortQueryConfiguration must be of kind 'select'")
                        data["port"] = port.execute()

                if isinstance(port, str):
                    # If port is a string, we assume it's an import path
                    data["port"] = get_import_path(port)

                    try:
                        data["port"] = data["port"]()
                    except Exception:
                        # Skip, might only run in situ
                        data["port"] = None

                if isinstance(port, (FunctionType, MethodType)):
                    # If port is a callable, we need to call it to get the Port instance
                    data["port_foo"] = get_import_path(port)

                    try:
                        data["port"] = data["port_foo"]()
                    except Exception:
                        # Skip, might only run in situ
                        data["port"] = None
        return data

    @field_validator("host", mode="before")
    @classmethod
    def _validate_host(cls, v):
        if v:
            if isinstance(v, str):
                v = get_import_path(v)

            if isinstance(v, (FunctionType, MethodType)):
                try:
                    # If it's a callable, we need to call it to get the Host instance
                    v = v()
                except Exception:
                    # Skip, might only run in situ
                    v = None

            if isinstance(v, HostQuery):
                if not v.kind == "select":
                    raise ValueError("BalancerHostQueryConfiguration must be of kind 'select'")
                v = v.execute()

            if isinstance(v, dict):
                v = TypeAdapter(Host).validate_python(v)
            assert v is None or isinstance(v, Host), f"host must be an instance of Host, got: {type(v)}"
        return v

    @field_validator("port", mode="before")
    @classmethod
    def _validate_port(cls, v):
        if v:
            if isinstance(v, str):
                v = get_import_path(v)

            if isinstance(v, (FunctionType, MethodType)):
                try:
                    # If it's a callable, we need to call it to get the Port instance
                    v = v()
                except Exception:
                    # Skip, might only run in situ
                    v = None

            if isinstance(v, PortQuery):
                if not v.kind == "select":
                    raise ValueError("BalancerPortQueryConfiguration must be of kind 'select'")
                v = v.execute()

            if isinstance(v, dict):
                v = TypeAdapter(Port).validate_python(v)
            assert v is None or isinstance(v, Port), f"port must be an instance of Port, got: {type(v)}"
        return v


# Alias
SupervisorSSHOperatorArgs = SupervisorSSHTaskArgs


class SupervisorSSHTask(Task, SupervisorSSHTaskArgs):
    operator: ImportPath = Field(default="airflow_supervisor.SupervisorSSH", validate_default=True)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: Type) -> Type:
        if not isinstance(v, Type) and issubclass(v, SupervisorSSHAirflowConfiguration):
            raise ValueError(f"operator must be 'airflow_supervisor.SupervisorSSH', got: {v}")
        return v


# Alias
SupervisorSSHOperator = SupervisorSSHTask
