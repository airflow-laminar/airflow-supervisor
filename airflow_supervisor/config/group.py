from pydantic import Field, field_serializer, field_validator
from typing import List, Optional

from .base import _BaseCfgModel

__all__ = ("GroupConfiguration",)


class GroupConfiguration(_BaseCfgModel):
    def to_cfg(self, key: str) -> str:
        # Overload to require key
        return super().to_cfg(key=key)

    programs: List[str] = Field(
        description="A comma-separated list of program names. The programs which are listed become members of the group."
    )
    priority: Optional[int] = Field(
        default=None, description="A priority number analogous to a [program:x] priority value assigned to the group."
    )

    @field_serializer("programs", when_used="json")
    def _dump_programs(self, v):
        if v:
            return ",".join(v)
        return None

    @field_validator("programs", mode="before")
    @classmethod
    def _load_programs(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v
