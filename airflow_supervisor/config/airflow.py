from pydantic import Field, SecretStr, field_serializer, field_validator, model_validator
from typing import List, Optional

from .base import HostPort, Signal, SupervisorLocation, UnixUserName, _BaseCfgModel

__all__ = ("AirflowConfiguration",)


class AirflowConfiguration(_BaseCfgModel):
    """Settings that MUST be set when running in airflow"""

    ############
    # programs #
    ############
    # autostart = False
    # autorestart = False
    startsecs: Optional[int] = Field(
        default=1,
        description="The total number of seconds which the program needs to stay running after a startup to consider the start successful (moving the process from the STARTING state to the RUNNING state). Set to 0 to indicate that the program needn’t stay running for any particular amount of time. Even if a process exits with an “expected” exit code (see exitcodes), the start will still be considered a failure if the process exits quicker than startsecs.",
    )
    startretries: Optional[int] = Field(
        default=None,
        description="The number of serial failure attempts that supervisord will allow when attempting to start the program before giving up and putting the process into an FATAL state. After each failed restart, process will be put in BACKOFF state and each retry attempt will take increasingly more time.",
    )
    exitcodes: Optional[List[int]] = Field(
        default=[0],
        description="The list of “expected” exit codes for this program used with autorestart. If the autorestart parameter is set to unexpected, and the process exits in any other way than as a result of a supervisor stop request, supervisord will restart the process if it exits with an exit code that is not defined in this list.",
    )
    stopsignal: Optional[Signal] = Field(
        default="TERM",
        description="The signal used to kill the program when a stop is requested. This can be specified using the signal’s name or its number. It is normally one of: TERM, HUP, INT, QUIT, KILL, USR1, or USR2.",
    )
    stopwaitsecs: Optional[int] = Field(
        default=30,
        description="The number of seconds to wait for the OS to return a SIGCHLD to supervisord after the program has been sent a stopsignal. If this number of seconds elapses before supervisord receives a SIGCHLD from the process, supervisord will attempt to kill it with a final SIGKILL.",
    )

    ####################
    # inet_http_server #
    ####################
    # port not optional
    port: HostPort = Field(
        default="*:9001",
        description="A TCP host:port value or (e.g. 127.0.0.1:9001) on which supervisor will listen for HTTP/XML-RPC requests. supervisorctl will use XML-RPC to communicate with supervisord over this port. To listen on all interfaces in the machine, use :9001 or *:9001. Please read the security warning above.",
    )
    username: Optional[UnixUserName] = Field(
        default=None, description="The username required for authentication to the HTTP/Unix Server."
    )
    password: Optional[SecretStr] = Field(
        default=None,
        description="he password required for authentication to the HTTP/Unix server. This can be a cleartext password, or can be specified as a SHA-1 hash if prefixed by the string {SHA}. For example, {SHA}82ab876d1387bfafe46cc1c8a2ef074eae50cb1d is the SHA-stored version of the password “thepassword”. Note that hashed password must be in hex format.",
    )

    #################
    # rpc_interface #
    ###################
    rpcinterface_factory: str = Field(
        default="supervisor.rpcinterface:make_main_rpcinterface",
        description="pkg_resources “entry point” dotted name to your RPC interface’s factory function.",
    )

    #########
    # Other #
    #########
    local_or_remote: Optional[SupervisorLocation] = Field(
        default="local",
        description="Location of supervisor, either local for same-machine or remote. If same-machine, communicates via Unix sockets by default, if remote, communicats via inet http server",
    )
    host: str = Field(
        default="localhost",
        description="Hostname of the supervisor host. Used by the XMLRPC client",
    )
    protocol: str = Field(
        default="http",
        description="Protocol of the supervisor XMLRPC HTTP API. Used by the XMLRPC client",
    )
    rpcpath: str = Field(
        default="/RPC2",
        description="Path for supervisor XMLRPC HTTP API. Used by the XMLRPC client",
    )

    @model_validator(mode="after")
    def validate_remote_accessible(self):
        if self.local_or_remote == "remote" and self.port.startswith(("localhost", "127.0.0.1")):
            raise ValueError("Supervisor binds only to loopback (localhost/127.0.0.1), but asked for remote")
        if self.local_or_remote == "remote" and self.host.startswith(("localhost", "127.0.0.1")):
            raise ValueError("Supervisor client expecting hostname, got localhost/127.0.0.1")
        return self

    @field_serializer("exitcodes", when_used="json")
    def _dump_exitcodes(self, v):
        if v:
            return ",".join(str(_) for _ in v)
        return None

    @field_validator("exitcodes", mode="before")
    @classmethod
    def _load_exitcodes(cls, v):
        if isinstance(v, str):
            v = v.split(",")
        if isinstance(v, list):
            return [int(_) for _ in v]
        return v
