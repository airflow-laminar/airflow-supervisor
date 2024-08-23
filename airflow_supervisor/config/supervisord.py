from pathlib import Path
from pydantic import Field, field_serializer, field_validator
from typing import Optional

from .base import LogLevel, OctalUmask, UnixUserName, _BaseCfgModel

__all__ = ("SupervisordConfiguration",)


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
    nodaemon: Optional[bool] = Field(
        default=None, description="If true, supervisord will start in the foreground instead of daemonizing."
    )
    silent: Optional[bool] = Field(
        default=None, description="If true and not daemonized, logs will not be directed to stdout."
    )
    minfds: Optional[int] = Field(
        default=None,
        description="The minimum number of file descriptors that must be available before supervisord will start successfully. A call to setrlimit will be made to attempt to raise the soft and hard limits of the supervisord process to satisfy minfds. The hard limit may only be raised if supervisord is run as root. supervisord uses file descriptors liberally, and will enter a failure mode when one cannot be obtained from the OS, so it’s useful to be able to specify a minimum value to ensure it doesn’t run out of them during execution. These limits will be inherited by the managed subprocesses. This option is particularly useful on Solaris, which has a low per-process fd limit by default.",
    )
    minprocs: Optional[int] = Field(
        default=None,
        description="The minimum number of process descriptors that must be available before supervisord will start successfully. A call to setrlimit will be made to attempt to raise the soft and hard limits of the supervisord process to satisfy minprocs. The hard limit may only be raised if supervisord is run as root. supervisord will enter a failure mode when the OS runs out of process descriptors, so it’s useful to ensure that enough process descriptors are available upon supervisord startup.",
    )
    nocleanup: Optional[bool] = Field(
        default=None,
        description="Prevent supervisord from clearing any existing AUTO child log files at startup time. Useful for debugging.",
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
    strip_ansi: Optional[bool] = Field(
        default=None, description="Strip all ANSI escape sequences from child log files."
    )
    environment: Optional[dict] = Field(
        default=None,
        description='A list of key/value pairs in the form KEY="val",KEY2="val2" that will be placed in the environment of all child processes. This does not change the environment of supervisord itself. This option can include the value %(here)s, which expands to the directory in which the supervisord configuration file was found. Values containing non-alphanumeric characters should be quoted (e.g. KEY="val:123",KEY2="val,456"). Otherwise, quoting the values is optional but recommended. To escape percent characters, simply use two. (e.g. URI="/first%%20name") Note that subprocesses will inherit the environment variables of the shell used to start supervisord except for the ones overridden here and within the program’s environment option. See Subprocess Environment.',
    )
    identifier: Optional[str] = Field(
        default=None, description="The identifier string for this supervisor process, used by the RPC interface."
    )

    @field_serializer("environment", when_used="json")
    def _dump_environment(self, v):
        if v:
            return ",".join(f"{k}={v}" for k, v in v.items())
        return None

    @field_validator("environment", mode="before")
    @classmethod
    def _load_environment(cls, v):
        if v:
            d = {}
            splits = v.split(",")
            for split in splits:
                split_splits = split.split("=")
                d[split_splits[0]] = split_splits[1]
            return d
        return v
