# airflow_supervisor.SupervisorConvenienceConfiguration

### *pydantic model* airflow_supervisor.SupervisorConvenienceConfiguration

Bases: [`SupervisorConfiguration`](airflow_supervisor.SupervisorConfiguration.md#airflow_supervisor.SupervisorConfiguration)

Convenience layer, settings that MUST be set when running via convenience API

#### *field* startsecs *: int | None* *= 1*

The total number of seconds which the program needs to stay running after a startup to consider the start successful (moving the process from the STARTING state to the RUNNING state). Set to 0 to indicate that the program needn’t stay running for any particular amount of time. Even if a process exits with an “expected” exit code (see exitcodes), the start will still be considered a failure if the process exits quicker than startsecs.

#### *field* startretries *: int | None* *= None*

The number of serial failure attempts that supervisord will allow when attempting to start the program before giving up and putting the process into an FATAL state. After each failed restart, process will be put in BACKOFF state and each retry attempt will take increasingly more time.

#### *field* exitcodes *: List[int] | None* *= [0]*

The list of “expected” exit codes for this program used with autorestart. If the autorestart parameter is set to unexpected, and the process exits in any other way than as a result of a supervisor stop request, supervisord will restart the process if it exits with an exit code that is not defined in this list.

#### *field* stopsignal *: Literal['TERM', 'HUP', 'INT', 'QUIT', 'KILL', 'USR1', 'USR2'] | None* *= 'TERM'*

The signal used to kill the program when a stop is requested. This can be specified using the signal’s name or its number. It is normally one of: TERM, HUP, INT, QUIT, KILL, USR1, or USR2.

#### *field* stopwaitsecs *: int | None* *= 30*

The number of seconds to wait for the OS to return a SIGCHLD to supervisord after the program has been sent a stopsignal. If this number of seconds elapses before supervisord receives a SIGCHLD from the process, supervisord will attempt to kill it with a final SIGKILL.

#### *field* stopasgroup *: bool | None* *= True*

If True, the stopsignal will be sent to the process group of the program, rather than just the program itself. This is useful for programs that spawn child processes.

#### *field* killasgroup *: bool | None* *= True*

If True, the stopsignal will be sent to the process group of the program, rather than just the program itself. This is useful for programs that spawn child processes.

#### *field* port *: Annotated[str, BeforeValidator(func=\_convert_to_host_port, json_schema_input_type=PydanticUndefined), AfterValidator(func=\_is_host_port)]* *= '\*:9001'*

A TCP host:port value or (e.g. 127.0.0.1:9001) on which supervisor will listen for HTTP/XML-RPC requests. supervisorctl will use XML-RPC to communicate with supervisord over this port. To listen on all interfaces in the machine, use :9001 or 

```
*
```

:9001. Please read the security warning above.

#### *field* username *: Annotated[str, AfterValidator(func=\_is_username)] | None* *= None*

The username required for authentication to the HTTP/Unix Server.

#### *field* password *: SecretStr | None* *= None*

The password required for authentication to the HTTP/Unix server. This can be a cleartext password, or can be specified as a SHA-1 hash if prefixed by the string {SHA}. For example, {SHA}82ab876d1387bfafe46cc1c8a2ef074eae50cb1d is the SHA-stored version of the password “thepassword”. Note that hashed password must be in hex format.

#### *field* rpcinterface_factory *: str* *= 'supervisor.rpcinterface:make_main_rpcinterface'*

pkg_resources “entry point” dotted name to your RPC interface’s factory function.

#### *field* local_or_remote *: Literal['local', 'remote'] | None* *= 'local'*

Location of supervisor, either local for same-machine or remote. If same-machine, communicates via Unix sockets by default, if remote, communicates via inet http server

#### *field* host *: str* *= 'localhost'*

Hostname of the supervisor host. Used by the XMLRPC client

#### *field* protocol *: str* *= 'http'*

Protocol of the supervisor XMLRPC HTTP API. Used by the XMLRPC client

#### *field* rpcpath *: str* *= '/RPC2'*

Path for supervisor XMLRPC HTTP API. Used by the XMLRPC client

#### *field* command_timeout *: int* *= 60*

Timeout for convenience commands sent to the supervisor, in seconds
