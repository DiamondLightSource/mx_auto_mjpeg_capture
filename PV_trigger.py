from ophyd_async.core import StandardReadable
from ophyd_async.epics.signal import epics_signal_rw


class PVTrigger(StandardReadable):
    def __init__(
        self,
    ) -> None:
        self.trigger = epics_signal_rw(float, "rpi:trigger:murko")

