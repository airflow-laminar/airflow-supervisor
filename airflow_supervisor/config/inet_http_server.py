from typing import Optional

from pydantic import Field, SecretStr, field_serializer

from .base import HostPort, UnixUserName, _BaseCfgModel

__all__ = ("InetHttpServerConfiguration",)


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

    port: Optional[HostPort] = Field(
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
