from typing import List, Optional

from pydantic import Field, field_serializer, field_validator

from .base import EventType
from .program import ProgramConfiguration

__all__ = ("EventListenerConfiguration",)


class EventListenerConfiguration(ProgramConfiguration):
    def to_cfg(self, key: str) -> str:
        # Overload to require key
        return super().to_cfg(key=key).replace("[event_listener", "[eventlistener")

    buffer_size: Optional[int] = Field(
        default=None,
        description="The event listener pool’s event queue buffer size. When a listener pool’s event buffer is overflowed (as can happen when an event listener pool cannot keep up with all of the events sent to it), the oldest event in the buffer is discarded.",
    )
    events: Optional[List[EventType]] = Field(
        default=None,
        description="A comma-separated list of event type names that this listener is “interested” in receiving notifications for (see Event Types for a list of valid event type names).",
    )
    result_handler: Optional[str] = Field(
        default=None,
        description="A pkg_resources entry point string that resolves to a Python callable. The default value is supervisor.dispatchers:default_handler. Specifying an alternate result handler is a very uncommon thing to need to do, and as a result, how to create one is not documented.",
    )

    # TODO can't inherit stdout_capture_maxbytes
    @field_validator("stdout_capture_maxbytes")
    @classmethod
    def _event_listener_cant_use_stdout_capture_maxbytes(cls, v: str) -> str:
        if v:
            raise ValueError("eventlistener cannot use stdout_capture_maxbytes")
        return None

    @field_serializer("events", when_used="json")
    def _dump_events(self, v):
        if v:
            return ",".join(v)
        return None

    @field_validator("events", mode="before")
    @classmethod
    def _load_events(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v
