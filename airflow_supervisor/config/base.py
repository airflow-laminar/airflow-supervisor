import re
from json import loads
from typing import Callable, Literal

from pydantic import BaseModel
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

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


def _is_host_port(v: str) -> str:
    splits = v.split(":")
    assert 0 < int(splits[1]) < 65_535
    return v


Octal = Annotated[str, AfterValidator(_is_octal(4))]
OctalUmask = Annotated[str, AfterValidator(_is_octal(3))]
UnixUserNameOrGroup = Annotated[str, AfterValidator(_is_username_or_usernamegroup)]
UnixUserName = Annotated[str, AfterValidator(_is_username)]
HostPort = Annotated[str, AfterValidator(_is_host_port)]
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
SupervisorLocation = Literal["local", "remote"]


class _BaseCfgModel(BaseModel):
    def to_cfg(self, key: str = "") -> str:
        ret = f"[{_snake_regex.sub('_', self.__class__.__name__.replace('Configuration', '')).lower()}{':' + key if key else ''}]"
        # round trip to json so we're fully
        # cfg-compatible
        for k, v in loads(self.model_dump_json()).items():
            if v is not None:
                if isinstance(v, bool):
                    ret += f"\n{k}={str(v).lower()}"
                else:
                    ret += f"\n{k}={v}"
        return ret.strip() + "\n"
