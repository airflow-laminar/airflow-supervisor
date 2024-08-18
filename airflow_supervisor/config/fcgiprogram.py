from typing import Optional

from pydantic import Field

from .base import Octal, UnixUserNameOrGroup
from .program import ProgramConfiguration

__all__ = ("FcgiProgramConfiguration",)


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
