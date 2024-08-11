import re
from datetime import UTC, datetime
from json import loads
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import (AnyUrl, BaseModel, Field, SecretStr, field_serializer,
                      field_validator)
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

__all__ = (
    "Octal",
    "OctalUmask",
    "UnixUserNameOrGroup",
    "UnixUserName",
    "LogLevel",
    "Signal",
    "UnixHttpServerConfiguration",
    "InetHttpServerConfiguration",
    "SupervisordConfiguration",
    "SupervisorctlConfiguration",
    "ProgramConfiguration",
    "IncludeConfiguration",
    "GroupConfiguration",
    "FcgiProgramConfiguration",
    "EventListenerConfiguration",
    "RpcInterfaceConfiguration",
    "SupervisorConfiguration",
)

_un_regex = re.compile(r"^[a-z_]([a-z0-9_-]{0,31}|[a-z0-9_-]{0,30}\$)$")
_snake_regex = re.compile(r"(?<!^)(?=[A-Z])")


def _is_octal(count: int) -> Callable[..., str]:
    def _check_is_octal(v: str) -> str:
        assert len(v) == count
        assert v[0] == "0"
        assert v
        for _ in range(count):
            assert 0 <= int(v[_]) <= 7
        return v

    return _check_is_octal


def _is_username(v: str) -> str:
    assert re.match(_un_regex, v)
    return v


def _is_username_or_usernamegroup(v: str) -> str:
    splits = v.split(":")
    assert len(splits) == 1 or len(splits) == 2
    assert re.match(_un_regex, splits[0])
    return v


def _generate_supervisor_config_path() -> Path:
    return Path(gettempdir()).resolve() / f"supervisor-{datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%S')}"


Octal = Annotated[str, AfterValidator(_is_octal(4))]
OctalUmask = Annotated[str, AfterValidator(_is_octal(3))]
UnixUserNameOrGroup = Annotated[str, AfterValidator(_is_username_or_usernamegroup)]
UnixUserName = Annotated[str, AfterValidator(_is_username)]
LogLevel = Literal["critical", "error", "warn", "info", "debug", "trace", "blather"]
Signal = Literal["TERM", "HUP", "INT", "QUIT", "KILL", "USR1", "USR2"]
EventType = Literal[
    "PROCESS_STATE",
    "PROCESS_STATE_STARTING",
    "PROCESS_STATE_RUNNING",
    "PROCESS_STATE_BACKOFF",
    "PROCESS_STATE_STOPPING",
    "PROCESS_STATE_EXITED",
    "PROCESS_STATE_STOPPED",
    "PROCESS_STATE_FATAL",
    "PROCESS_STATE_UNKNOWN",
    "REMOTE_COMMUNICATION",
    "PROCESS_LOG",
    "PROCESS_LOG_STDOUT",
    "PROCESS_LOG_STDERR",
    "PROCESS_COMMUNICATION",
    "PROCESS_COMMUNICATION_STDOUT",
    "PROCESS_COMMUNICATION_STDERR",
    "SUPERVISOR_STATE_CHANGE",
    "SUPERVISOR_STATE_CHANGE_RUNNING",
    "SUPERVISOR_STATE_CHANGE_STOPPING",
    "TICK",
    "TICK_5",
    "TICK_60",
    "TICK_3600",
    "PROCESS_GROUP",
    "PROCESS_GROUP_ADDED",
    "PROCESS_GROUP_REMOVED",
]


class _BaseCfgModel(BaseModel):
    def to_cfg(self, key: str = "") -> str:
        ret = f"[{_snake_regex.sub('_', self.__class__.__name__.replace('Configuration', '')).lower()}{':' + key if key else ''}]"
        # round trip to json so we're fully
        # cfg-compatible
        for k, v in loads(self.model_dump_json()).items():
            if v:
                ret += f"\n{k}={v}"
        return ret.strip() + "\n"


class UnixHttpServerConfiguration(_BaseCfgModel):
    file: Optional[Path] = Field(
        default=None,
        description="A path to a UNIX domain socket on which supervisor will listen for HTTP/XML-RPC requests. supervisorctl uses XML-RPC to communicate with supervisord over this port. This option can include the value %(here)s, which expands to the directory in which the supervisord configuration file was found.",
    )
    chmod: Optional[Octal] = Field(
        default=None, description="Change the UNIX permission mode bits of the UNIX domain socket to this value at startup."
    )
    chown: Optional[UnixUserNameOrGroup] = Field(
        default=None,
        description="Change the user and group of the socket file to this value. May be a UNIX username (e.g. chrism) or a UNIX username and group separated by a colon (e.g. chrism:wheel).",
    )
    username: Optional[UnixUserName] = Field(default=None, description="The username required for authentication to this HTTP server.")
    password: Optional[SecretStr] = Field(
        default=None,
        description="The password required for authentication to this HTTP server. This can be a cleartext password, or can be specified as a SHA-1 hash if prefixed by the string {SHA}. For example, {SHA}82ab876d1387bfafe46cc1c8a2ef074eae50cb1d is the SHA-stored version of the password “thepassword”. Note that hashed password must be in hex format.",
    )

    @field_serializer("password", when_used="json")
    def _dump_password(self, v):
        return v.get_secret_value() if v else None


class InetHttpServerConfiguration(_BaseCfgModel):
    def to_cfg(self) -> str:
        ret = "[inet_http_server]"
        if self.port:
            ret += f"\nport={self.port}"
        if self.username:
            ret += f"\nusername={self.username}"
        if self.password:
            ret += f"\npassword={self.password.get_secret_value()}"
        return ret.strip() + "\n"

    port: Optional[str] = Field(
        default=None,
        description="A TCP host:port value or (e.g. 127.0.0.1:9001) on which supervisor will listen for HTTP/XML-RPC requests. supervisorctl will use XML-RPC to communicate with supervisord over this port. To listen on all interfaces in the machine, use :9001 or *:9001. Please read the security warning above.",
    )
    username: Optional[UnixUserName] = Field(default=None, description="The username required for authentication to this HTTP server.")
    password: Optional[SecretStr] = Field(
        default=None,
        description="he password required for authentication to this HTTP server. This can be a cleartext password, or can be specified as a SHA-1 hash if prefixed by the string {SHA}. For example, {SHA}82ab876d1387bfafe46cc1c8a2ef074eae50cb1d is the SHA-stored version of the password “thepassword”. Note that hashed password must be in hex format.",
    )

    @field_serializer("password", when_used="json")
    def _dump_password(self, v):
        return v.get_secret_value() if v else None


class SupervisordConfiguration(_BaseCfgModel):
    logfile: Optional[Path] = Field(
        default=None,
        description="The path to the activity log of the supervisord process. This option can include the value %(here)s, which expands to the directory in which the supervisord configuration file was found.",
    )
    logfile_maxbytes: Optional[str] = Field(
        default=None,
        description="The maximum number of bytes that may be consumed by the activity log file before it is rotated (suffix multipliers like “KB”, “MB”, and “GB” can be used in the value). Set this value to 0 to indicate an unlimited log size.",
    )
    logfile_backups: Optional[int] = Field(
        default=None,
        description="The number of backups to keep around resulting from activity log file rotation. If set to 0, no backups will be kept.",
    )
    loglevel: Optional[LogLevel] = Field(
        default=None,
        description="The logging level, dictating what is written to the supervisord activity log. One of critical, error, warn, info, debug, trace, or blather. Note that at log level debug, the supervisord log file will record the stderr/stdout output of its child processes and extended info about process state changes, which is useful for debugging a process which isn’t starting properly. See also: Activity Log Levels.",
    )
    pidfile: Optional[Path] = Field(
        default=None,
        description="The location in which supervisord keeps its pid file. This option can include the value %(here)s, which expands to the directory in which the supervisord configuration file was found.",
    )
    umask: Optional[OctalUmask] = Field(default=None, description="The umask of the supervisord process.")
    nodaemon: Optional[bool] = Field(default=None, description="If true, supervisord will start in the foreground instead of daemonizing.")
    silent: Optional[bool] = Field(default=None, description="If true and not daemonized, logs will not be directed to stdout.")
    minfds: Optional[int] = Field(
        default=None,
        description="The minimum number of file descriptors that must be available before supervisord will start successfully. A call to setrlimit will be made to attempt to raise the soft and hard limits of the supervisord process to satisfy minfds. The hard limit may only be raised if supervisord is run as root. supervisord uses file descriptors liberally, and will enter a failure mode when one cannot be obtained from the OS, so it’s useful to be able to specify a minimum value to ensure it doesn’t run out of them during execution. These limits will be inherited by the managed subprocesses. This option is particularly useful on Solaris, which has a low per-process fd limit by default.",
    )
    minprocs: Optional[int] = Field(
        default=None,
        description="The minimum number of process descriptors that must be available before supervisord will start successfully. A call to setrlimit will be made to attempt to raise the soft and hard limits of the supervisord process to satisfy minprocs. The hard limit may only be raised if supervisord is run as root. supervisord will enter a failure mode when the OS runs out of process descriptors, so it’s useful to ensure that enough process descriptors are available upon supervisord startup.",
    )
    nocleanup: Optional[bool] = Field(
        default=None, description="Prevent supervisord from clearing any existing AUTO child log files at startup time. Useful for debugging."
    )
    childlogdir: Optional[Path] = Field(
        default=None,
        description="The directory used for AUTO child log files. This option can include the value %(here)s, which expands to the directory in which the supervisord configuration file was found.",
    )
    user: Optional[UnixUserName] = Field(
        default=None,
        description="Instruct supervisord to switch users to this UNIX user account before doing any meaningful processing. The user can only be switched if supervisord is started as the root user.",
    )
    directory: Optional[Path] = Field(
        default=None,
        description="When supervisord daemonizes, switch to this directory. This option can include the value %(here)s, which expands to the directory in which the supervisord configuration file was found.",
    )
    strip_ansi: Optional[bool] = Field(default=None, description="Strip all ANSI escape sequences from child log files.")
    environment: Optional[dict] = Field(
        default=None,
        description='A list of key/value pairs in the form KEY="val",KEY2="val2" that will be placed in the environment of all child processes. This does not change the environment of supervisord itself. This option can include the value %(here)s, which expands to the directory in which the supervisord configuration file was found. Values containing non-alphanumeric characters should be quoted (e.g. KEY="val:123",KEY2="val,456"). Otherwise, quoting the values is optional but recommended. To escape percent characters, simply use two. (e.g. URI="/first%%20name") Note that subprocesses will inherit the environment variables of the shell used to start supervisord except for the ones overridden here and within the program’s environment option. See Subprocess Environment.',
    )
    identifier: Optional[str] = Field(default=None, description="The identifier string for this supervisor process, used by the RPC interface.")

    @field_serializer("environment", when_used="json")
    def _dump_environment(self, v):
        if v:
            return ",".join(f"{k}={v}" for k, v in v.items())
        return None


class SupervisorctlConfiguration(_BaseCfgModel):
    serverurl: Optional[AnyUrl] = Field(
        default=None,
        description="The URL that should be used to access the supervisord server, e.g. http://localhost:9001. For UNIX domain sockets, use unix:///absolute/path/to/file.sock.",
    )
    username: Optional[UnixUserName] = Field(
        default=None,
        description="The username to pass to the supervisord server for use in authentication. This should be same as username from the supervisord server configuration for the port or UNIX domain socket you’re attempting to access.",
    )
    password: Optional[SecretStr] = Field(
        default=None,
        description="The password to pass to the supervisord server for use in authentication. This should be the cleartext version of password from the supervisord server configuration for the port or UNIX domain socket you’re attempting to access. This value cannot be passed as a SHA hash. Unlike other passwords specified in this file, it must be provided in cleartext.",
    )
    prompt: Optional[str] = Field(default=None, description="String used as supervisorctl prompt.")
    history_file: Optional[Path] = Field(
        default=None,
        description="A path to use as the readline persistent history file. If you enable this feature by choosing a path, your supervisorctl commands will be kept in the file, and you can use readline (e.g. arrow-up) to invoke commands you performed in your last supervisorctl session.",
    )

    @field_serializer("password", when_used="json")
    def _dump_password(self, v):
        return v.get_secret_value() if v else None


class ProgramConfiguration(_BaseCfgModel):
    def to_cfg(self, key: str) -> str:
        # Overload to require key
        return super().to_cfg(key=key)

    command: str = Field(
        description="The command that will be run when this program is started. The command can be either absolute (e.g. /path/to/programname) or relative (e.g. programname). If it is relative, the supervisord’s environment $PATH will be searched for the executable. Programs can accept arguments, e.g. /path/to/program foo bar. The command line can use double quotes to group arguments with spaces in them to pass to the program, e.g. /path/to/program/name -p 'foo bar'. Note that the value of command may include Python string expressions, e.g. /path/to/programname --port=80%(process_num)02d might expand to /path/to/programname --port=8000 at runtime. String expressions are evaluated against a dictionary containing the keys group_name, host_node_name, program_name, process_num, numprocs, here (the directory of the supervisord config file), and all supervisord’s environment variables prefixed with ENV_. Controlled programs should themselves not be daemons, as supervisord assumes it is responsible for daemonizing its subprocesses (see Nondaemonizing of Subprocesses). The command will be truncated if it looks like a config file comment, e.g. command=bash -c 'foo ; bar' will be truncated to command=bash -c 'foo. Quoting will not prevent this behavior, since the configuration file reader does not parse the command like a shell would."
    )
    process_name: Optional[str] = Field(
        default=None,
        description="A Python string expression that is used to compose the supervisor process name for this process. You usually don’t need to worry about setting this unless you change numprocs. The string expression is evaluated against a dictionary that includes group_name, host_node_name, process_num, program_name, and here (the directory of the supervisord config file).",
    )
    numprocs: Optional[int] = Field(
        default=None,
        description="Supervisor will start as many instances of this program as named by numprocs. Note that if numprocs > 1, the process_name expression must include %(process_num)s (or any other valid Python string expression that includes process_num) within it.",
    )
    numprocs_start: Optional[int] = Field(
        default=None, description="An integer offset that is used to compute the number at which process_num starts."
    )
    priority: Optional[int] = Field(
        default=None,
        description="The relative priority of the program in the start and shutdown ordering. Lower priorities indicate programs that start first and shut down last at startup and when aggregate commands are used in various clients (e.g. “start all”/”stop all”). Higher priorities indicate programs that start last and shut down first.",
    )
    autostart: Optional[bool] = Field(default=None, description="If true, this program will start automatically when supervisord is started.")
    startsecs: Optional[int] = Field(
        default=None,
        description="The total number of seconds which the program needs to stay running after a startup to consider the start successful (moving the process from the STARTING state to the RUNNING state). Set to 0 to indicate that the program needn’t stay running for any particular amount of time. Even if a process exits with an “expected” exit code (see exitcodes), the start will still be considered a failure if the process exits quicker than startsecs.",
    )
    startretries: Optional[int] = Field(
        default=None,
        description="The number of serial failure attempts that supervisord will allow when attempting to start the program before giving up and putting the process into an FATAL state. After each failed restart, process will be put in BACKOFF state and each retry attempt will take increasingly more time.",
    )
    autorestart: Optional[str] = Field(
        default=None,
        description="Specifies if supervisord should automatically restart a process if it exits when it is in the RUNNING state. May be one of false, unexpected, or true. If false, the process will not be autorestarted. If unexpected, the process will be restarted when the program exits with an exit code that is not one of the exit codes associated with this process’ configuration (see exitcodes). If true, the process will be unconditionally restarted when it exits, without regard to its exit code. autorestart controls whether supervisord will autorestart a program if it exits after it has successfully started up (the process is in the RUNNING state). supervisord has a different restart mechanism for when the process is starting up (the process is in the STARTING state). Retries during process startup are controlled by startsecs and startretries.",
    )
    exitcodes: Optional[List[int]] = Field(
        default=None,
        description="The list of “expected” exit codes for this program used with autorestart. If the autorestart parameter is set to unexpected, and the process exits in any other way than as a result of a supervisor stop request, supervisord will restart the process if it exits with an exit code that is not defined in this list.",
    )
    stopsignal: Optional[Signal] = Field(
        default=None,
        description="The signal used to kill the program when a stop is requested. This can be specified using the signal’s name or its number. It is normally one of: TERM, HUP, INT, QUIT, KILL, USR1, or USR2.",
    )
    stopwaitsecs: Optional[int] = Field(
        default=None,
        description="The number of seconds to wait for the OS to return a SIGCHLD to supervisord after the program has been sent a stopsignal. If this number of seconds elapses before supervisord receives a SIGCHLD from the process, supervisord will attempt to kill it with a final SIGKILL.",
    )
    stopasgroup: Optional[bool] = Field(
        default=None,
        description="If true, the flag causes supervisor to send the stop signal to the whole process group and implies killasgroup is true. This is useful for programs, such as Flask in debug mode, that do not propagate stop signals to their children, leaving them orphaned.",
    )
    killasgroup: Optional[bool] = Field(
        default=None,
        description="If true, when resorting to send SIGKILL to the program to terminate it send it to its whole process group instead, taking care of its children as well, useful e.g with Python programs using multiprocessing.",
    )
    user: Optional[UnixUserName] = Field(
        default=None,
        description="Instruct supervisord to use this UNIX user account as the account which runs the program. The user can only be switched if supervisord is run as the root user. If supervisord can’t switch to the specified user, the program will not be started. The user will be changed using setuid only. This does not start a login shell and does not change environment variables like USER or HOME. See Subprocess Environment for details.",
    )
    redirect_stderr: Optional[bool] = Field(
        default=None,
        description="If true, cause the process’ stderr output to be sent back to supervisord on its stdout file descriptor (in UNIX shell terms, this is the equivalent of executing /the/program 2>&1). Do not set redirect_stderr=true in an [eventlistener:x] section. Eventlisteners use stdout and stdin to communicate with supervisord. If stderr is redirected, output from stderr will interfere with the eventlistener protocol.",
    )
    stdout_logfile: Optional[Path] = Field(
        default=None,
        description="Put process stdout output in this file (and if redirect_stderr is true, also place stderr output in this file). If stdout_logfile is unset or set to AUTO, supervisor will automatically choose a file location. If this is set to NONE, supervisord will create no log file. AUTO log files and their backups will be deleted when supervisord restarts. The stdout_logfile value can contain Python string expressions that will evaluated against a dictionary that contains the keys group_name, host_node_name, process_num, program_name, and here (the directory of the supervisord config file). It is not possible for two processes to share a single log file (stdout_logfile) when rotation (stdout_logfile_maxbytes) is enabled. This will result in the file being corrupted. If stdout_logfile is set to a special file like /dev/stdout that is not seekable, log rotation must be disabled by setting stdout_logfile_maxbytes = 0.",
    )
    stdout_logfile_maxbytes: Optional[str] = Field(
        default=None,
        description="The maximum number of bytes that may be consumed by stdout_logfile before it is rotated (suffix multipliers like “KB”, “MB”, and “GB” can be used in the value). Set this value to 0 to indicate an unlimited log size.",
    )
    stdout_logfile_backups: Optional[int] = Field(
        default=None,
        description="The number of stdout_logfile backups to keep around resulting from process stdout log file rotation. If set to 0, no backups will be kept.",
    )
    stdout_capture_maxbytes: Optional[int] = Field(
        default=None,
        description="Max number of bytes written to capture FIFO when process is in “stdout capture mode” (see Capture Mode). Should be an integer (suffix multipliers like “KB”, “MB” and “GB” can used in the value). If this value is 0, process capture mode will be off.",
    )
    stdout_events_enabled: Optional[int] = Field(
        default=None,
        description="If true, PROCESS_LOG_STDOUT events will be emitted when the process writes to its stdout file descriptor. The events will only be emitted if the file descriptor is not in capture mode at the time the data is received (see Capture Mode).",
    )
    stdout_syslog: Optional[bool] = Field(default=None, description="If true, stdout will be directed to syslog along with the process name.")
    stderr_logfile: Optional[Path] = Field(
        default=None,
        description="Put process stderr output in this file unless redirect_stderr is true. Accepts the same value types as stdout_logfile and may contain the same Python string expressions. It is not possible for two processes to share a single log file (stderr_logfile) when rotation (stderr_logfile_maxbytes) is enabled. This will result in the file being corrupted. If stderr_logfile is set to a special file like /dev/stderr that is not seekable, log rotation must be disabled by setting stderr_logfile_maxbytes = 0.",
    )
    stderr_logfile_maxbytes: Optional[str] = Field(
        default=None,
        description="The maximum number of bytes before logfile rotation for stderr_logfile. Accepts the same value types as stdout_logfile_maxbytes.",
    )
    stderr_logfile_backups: Optional[int] = Field(
        default=None,
        description="The number of backups to keep around resulting from process stderr log file rotation. If set to 0, no backups will be kept.",
    )
    stderr_capture_maxbytes: Optional[int] = Field(
        default=None,
        description="Max number of bytes written to capture FIFO when process is in “stderr capture mode” (see Capture Mode). Should be an integer (suffix multipliers like “KB”, “MB” and “GB” can used in the value). If this value is 0, process capture mode will be off.",
    )
    stderr_events_enabled: Optional[bool] = Field(
        default=None,
        description="If true, PROCESS_LOG_STDERR events will be emitted when the process writes to its stderr file descriptor. The events will only be emitted if the file descriptor is not in capture mode at the time the data is received (see Capture Mode).",
    )
    stderr_syslog: Optional[bool] = Field(default=None, description="If true, stderr will be directed to syslog along with the process name.")
    environment: Optional[Dict[str, str]] = Field(
        default=None,
        description='A list of key/value pairs in the form KEY="val",KEY2="val2" that will be placed in the child process’ environment. The environment string may contain Python string expressions that will be evaluated against a dictionary containing group_name, host_node_name, process_num, program_name, and here (the directory of the supervisord config file). Values containing non-alphanumeric characters should be quoted (e.g. KEY="val:123",KEY2="val,456"). Otherwise, quoting the values is optional but recommended. Note that the subprocess will inherit the environment variables of the shell used to start “supervisord” except for the ones overridden here. See Subprocess Environment.',
    )
    directory: Optional[Path] = Field(
        default=None, description="A file path representing a directory to which supervisord should temporarily chdir before exec’ing the child."
    )
    umask: Optional[OctalUmask] = Field(default=None, description="An octal number (e.g. 002, 022) representing the umask of the process.")
    serverurl: Optional[str] = Field(
        default=None,
        description="The URL passed in the environment to the subprocess process as SUPERVISOR_SERVER_URL (see supervisor.childutils) to allow the subprocess to easily communicate with the internal HTTP server. If provided, it should have the same syntax and structure as the [supervisorctl] section option of the same name. If this is set to AUTO, or is unset, supervisor will automatically construct a server URL, giving preference to a server that listens on UNIX domain sockets over one that listens on an internet socket.",
    )

    @field_serializer("exitcodes", when_used="json")
    def _dump_exitcodes(self, v):
        if v:
            return ",".join(v)
        return None


class IncludeConfiguration(_BaseCfgModel):
    files: List[str] = Field(
        description="A space-separated sequence of file globs. Each file glob may be absolute or relative. If the file glob is relative, it is considered relative to the location of the configuration file which includes it. A “glob” is a file pattern which matches a specified pattern according to the rules used by the Unix shell. No tilde expansion is done, but *, ?, and character ranges expressed with [] will be correctly matched. The string expression is evaluated against a dictionary that includes host_node_name and here (the directory of the supervisord config file). Recursive includes from included files are not supported."
    )

    @field_serializer("files", when_used="json")
    def _dump_files(self, v):
        if v:
            return " ".join(v)
        return None


class GroupConfiguration(_BaseCfgModel):
    def to_cfg(self, key: str) -> str:
        # Overload to require key
        return super().to_cfg(key=key)

    programs: List[str] = Field(description="A comma-separated list of program names. The programs which are listed become members of the group.")
    priority: Optional[int] = Field(default=None, description="A priority number analogous to a [program:x] priority value assigned to the group.")

    @field_serializer("programs", when_used="json")
    def _dump_programs(self, v):
        if v:
            return ",".join(v)
        return None


class FcgiProgramConfiguration(ProgramConfiguration):
    def to_cfg(self, key: str) -> str:
        # Overload to require key
        return super().to_cfg(key=key).replace("[fcgi_program", "[fcgi-program")

    socket: str = Field(
        description="The FastCGI socket for this program, either TCP or UNIX domain socket. For TCP sockets, use this format: tcp://localhost:9002. For UNIX domain sockets, use unix:///absolute/path/to/file.sock. String expressions are evaluated against a dictionary containing the keys “program_name” and “here” (the directory of the supervisord config file)."
    )
    socket_backlog: Optional[str] = Field(default=None, description="Sets socket listen(2) backlog.")
    socket_owner: Optional[UnixUserNameOrGroup] = Field(
        default=None,
        description="For UNIX domain sockets, this parameter can be used to specify the user and group for the FastCGI socket. May be a UNIX username (e.g. chrism) or a UNIX username and group separated by a colon (e.g. chrism:wheel).",
    )
    socket_mode: Optional[Octal] = Field(
        default=None, description="For UNIX domain sockets, this parameter can be used to specify the permission mode."
    )


class EventListenerConfiguration(ProgramConfiguration):
    def to_cfg(self, key: str) -> str:
        # Overload to require key
        return super().to_cfg(key=key).replace("[event_listener", "[eventlistener")

    buffer_size: Optional[int] = Field(
        default=None,
        description="The event listener pool’s event queue buffer size. When a listener pool’s event buffer is overflowed (as can happen when an event listener pool cannot keep up with all of the events sent to it), the oldest event in the buffer is discarded.",
    )
    events: Optional[List[EventType]] = Field(
        default=None,
        description="A comma-separated list of event type names that this listener is “interested” in receiving notifications for (see Event Types for a list of valid event type names).",
    )
    result_handler: Optional[str] = Field(
        default=None,
        description="A pkg_resources entry point string that resolves to a Python callable. The default value is supervisor.dispatchers:default_handler. Specifying an alternate result handler is a very uncommon thing to need to do, and as a result, how to create one is not documented.",
    )

    # TODO can't inherit stdout_capture_maxbytes
    @field_validator("stdout_capture_maxbytes")
    @classmethod
    def _event_listener_cant_use_stdout_capture_maxbytes(cls, v: str) -> str:
        raise ValueError("eventlistener cannot use stdout_capture_maxbytes")

    @field_serializer("events", when_used="json")
    def _dump_events(self, v):
        if v:
            return ",".join(v)
        return None


class RpcInterfaceConfiguration(_BaseCfgModel):
    def to_cfg(self, key: str) -> str:
        # Overload to require key
        return super().to_cfg(key=key).replace("[rpc_interface", "[rpcinterface")

    supervisor_rpcinterface_factory: str = Field(description="pkg_resources “entry point” dotted name to your RPC interface’s factory function.")
    kwargs: Optional[Dict[str, Any]] = Field(default=None)  # TODO


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
    unix_http_server: UnixHttpServerConfiguration = Field(default=None)
    inet_http_server: InetHttpServerConfiguration = Field(default=None)
    supervisord: SupervisordConfiguration = Field(default=None)
    supervisorctl: SupervisorctlConfiguration = Field(default=None)
    include: Optional[IncludeConfiguration] = Field(default=None)

    program: Dict[str, ProgramConfiguration]
    group: Optional[Dict[str, GroupConfiguration]] = Field(default=None)

    fcgiprogram: Optional[Dict[str, FcgiProgramConfiguration]] = Field(default=None)
    eventlistener: Optional[Dict[str, EventListenerConfiguration]] = Field(default=None)
    rpcinterface: Optional[Dict[str, RpcInterfaceConfiguration]] = Field(default=None)

    # other configuration
    path: Optional[Path] = Field(default_factory=_generate_supervisor_config_path, description="Path to supervisor configuration")
