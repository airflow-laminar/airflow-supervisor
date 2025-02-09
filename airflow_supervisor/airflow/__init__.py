from .local import *

try:
    from .ssh import *
except ImportError:
    pass
