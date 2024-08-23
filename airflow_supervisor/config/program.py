from pathlib import Path
from pydantic import Field, field_serializer, field_validator
from typing import Dict, List, Literal, Optional, Union

from .base import OctalUmask, Signal, UnixUserName, _BaseCfgModel

__all__ = ("ProgramConfiguration",)


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
    autostart: Optional[bool] = Field(
        default=None, description="If true, this program will start automatically when supervisord is started."
    )
    startsecs: Optional[int] = Field(
        default=None,
        description="The total number of seconds which the program needs to stay running after a startup to consider the start successful (moving the process from the STARTING state to the RUNNING state). Set to 0 to indicate that the program needn’t stay running for any particular amount of time. Even if a process exits with an “expected” exit code (see exitcodes), the start will still be considered a failure if the process exits quicker than startsecs.",
    )
    startretries: Optional[int] = Field(
        default=None,
        description="The number of serial failure attempts that supervisord will allow when attempting to start the program before giving up and putting the process into an FATAL state. After each failed restart, process will be put in BACKOFF state and each retry attempt will take increasingly more time.",
    )
    autorestart: Optional[Union[bool, Literal["unexpected"]]] = Field(
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
    stdout_syslog: Optional[bool] = Field(
        default=None, description="If true, stdout will be directed to syslog along with the process name."
    )
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
    stderr_syslog: Optional[bool] = Field(
        default=None, description="If true, stderr will be directed to syslog along with the process name."
    )
    environment: Optional[Dict[str, str]] = Field(
        default=None,
        description='A list of key/value pairs in the form KEY="val",KEY2="val2" that will be placed in the child process’ environment. The environment string may contain Python string expressions that will be evaluated against a dictionary containing group_name, host_node_name, process_num, program_name, and here (the directory of the supervisord config file). Values containing non-alphanumeric characters should be quoted (e.g. KEY="val:123",KEY2="val,456"). Otherwise, quoting the values is optional but recommended. Note that the subprocess will inherit the environment variables of the shell used to start “supervisord” except for the ones overridden here. See Subprocess Environment.',
    )
    directory: Optional[Path] = Field(
        default=None,
        description="A file path representing a directory to which supervisord should temporarily chdir before exec’ing the child.",
    )
    umask: Optional[OctalUmask] = Field(
        default=None, description="An octal number (e.g. 002, 022) representing the umask of the process."
    )
    serverurl: Optional[str] = Field(
        default=None,
        description="The URL passed in the environment to the subprocess process as SUPERVISOR_SERVER_URL (see supervisor.childutils) to allow the subprocess to easily communicate with the internal HTTP server. If provided, it should have the same syntax and structure as the [supervisorctl] section option of the same name. If this is set to AUTO, or is unset, supervisor will automatically construct a server URL, giving preference to a server that listens on UNIX domain sockets over one that listens on an internet socket.",
    )

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

    @field_serializer("autorestart", when_used="json")
    def _dump_autorestart(self, v):
        if isinstance(v, bool):
            return str(v).lower()
        elif isinstance(v, str):
            return v.lower()
        return None

    @field_validator("autorestart", mode="before")
    @classmethod
    def _load_autorestart(cls, v):
        if isinstance(v, str):
            # handle string -> bool
            if v.lower() == "false":
                return False
            if v.lower() == "true":
                return True
        return v
