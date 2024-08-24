from pathlib import Path
from typing import Optional

from pydantic import AnyUrl, Field, SecretStr, field_serializer

from .base import UnixUserName, _BaseCfgModel

__all__ = ("SupervisorctlConfiguration",)


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
