from .local import SupervisorLocal

try:
    from .ssh import SupervisorRemote
except ImportError:
    ...
