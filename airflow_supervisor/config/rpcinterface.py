from typing import Any, Dict, Optional

from pydantic import Field
from .base import _BaseCfgModel

__all__ = ("RpcInterfaceConfiguration",)


class RpcInterfaceConfiguration(_BaseCfgModel):
    def to_cfg(self, key: str) -> str:
        # Overload to require key
        return super().to_cfg(key=key).replace("[rpc_interface", "[rpcinterface")

    supervisor_rpcinterface_factory: str = Field(description="pkg_resources “entry point” dotted name to your RPC interface’s factory function.")
    kwargs: Optional[Dict[str, Any]] = Field(default=None)  # TODO
