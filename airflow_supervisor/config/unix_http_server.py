from pathlib import Path
from pydantic import Field, SecretStr, field_serializer
from typing import Optional

from .base import Octal, UnixUserName, UnixUserNameOrGroup, _BaseCfgModel

__all__ = ("UnixHttpServerConfiguration",)


class UnixHttpServerConfiguration(_BaseCfgModel):
    file: Optional[Path] = Field(
        default=None,
        description="A path to a UNIX domain socket on which supervisor will listen for HTTP/XML-RPC requests. supervisorctl uses XML-RPC to communicate with supervisord over this port. This option can include the value %(here)s, which expands to the directory in which the supervisord configuration file was found.",
    )
    chmod: Optional[Octal] = Field(
        default=None,
        description="Change the UNIX permission mode bits of the UNIX domain socket to this value at startup.",
    )
    chown: Optional[UnixUserNameOrGroup] = Field(
        default=None,
        description="Change the user and group of the socket file to this value. May be a UNIX username (e.g. chrism) or a UNIX username and group separated by a colon (e.g. chrism:wheel).",
    )
    username: Optional[UnixUserName] = Field(
        default=None, description="The username required for authentication to this HTTP server."
    )
    password: Optional[SecretStr] = Field(
        default=None,
        description="The password required for authentication to this HTTP server. This can be a cleartext password, or can be specified as a SHA-1 hash if prefixed by the string {SHA}. For example, {SHA}82ab876d1387bfafe46cc1c8a2ef074eae50cb1d is the SHA-stored version of the password “thepassword”. Note that hashed password must be in hex format.",
    )

    @field_serializer("password", when_used="json")
    def _dump_password(self, v):
        return v.get_secret_value() if v else None
