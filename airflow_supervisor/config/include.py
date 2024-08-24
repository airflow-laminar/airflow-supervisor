from typing import List

from pydantic import Field, field_serializer, field_validator

from .base import _BaseCfgModel

__all__ = ("IncludeConfiguration",)


class IncludeConfiguration(_BaseCfgModel):
    files: List[str] = Field(
        description="A space-separated sequence of file globs. Each file glob may be absolute or relative. If the file glob is relative, it is considered relative to the location of the configuration file which includes it. A “glob” is a file pattern which matches a specified pattern according to the rules used by the Unix shell. No tilde expansion is done, but *, ?, and character ranges expressed with [] will be correctly matched. The string expression is evaluated against a dictionary that includes host_node_name and here (the directory of the supervisord config file). Recursive includes from included files are not supported."
    )

    @field_serializer("files", when_used="json")
    def _dump_files(self, v):
        if v:
            return " ".join(v)
        return None

    @field_validator("files", mode="before")
    @classmethod
    def _load_files(cls, v):
        if isinstance(v, str):
            return v.split(" ")
        return v
