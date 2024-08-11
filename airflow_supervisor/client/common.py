from ..config import SupervisorConfiguration


class SupervisorClientBase(object):
    def __init__(self, cfg: SupervisorConfiguration):
        self._cfg = cfg
