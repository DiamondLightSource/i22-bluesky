import bluesky.plan_stubs as bps
from dls_bluesky_core.stubs.flyables import fly_and_collect
from ophyd_async.core import HardwareTriggeredFlyable

from i22_bluesky.panda.fly_scanning import RepeatedTrigger


def send_triggers(flyer: HardwareTriggeredFlyable, exposure: float, deadtime: float):
    """Send some triggers to detectors and wait for them to collect."""
    # Do a single batch to start
    yield from fly_and_collect(flyer)
    # Setup for many batches
    many_batches = RepeatedTrigger(
        num=(1 / exposure),
        width=exposure,
        deadtime=deadtime,
        repeats=9,
        period=60,
    )
    yield from bps.mv(flyer, many_batches)
    # Then start flying, collecting roughly every step
    yield from fly_and_collect(flyer)
