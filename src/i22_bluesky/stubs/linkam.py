import bluesky.plan_stubs as bps
import numpy as np
from dls_bluesky_core.core import group_uuid, step_to_num
from dls_bluesky_core.stubs.flyables import fly_and_collect
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core.flyer import HardwareTriggeredFlyable

from i22_bluesky.panda.fly_scanning import RepeatedTrigger


# TODO: Make non-flyer signature to allow non-flying with non-flying device?
def scan_linkam(
    linkam: Linkam3,
    flyer: HardwareTriggeredFlyable,
    start: float,
    stop: float,
    step: float,
    rate: float, # deg C/min
    exposure: float,
    deadtime: float,
    num_frames: int,
    fly=False,
):
    one_batch = RepeatedTrigger(num=num_frames, width=exposure, deadtime=deadtime)
    start, stop, num = step_to_num(start, stop, step)
    yield from bps.mv(linkam.ramp_rate, rate ) 
    if fly:
        # Do a single batch to start
        yield from bps.mv(linkam, start, flyer, one_batch)
        yield from fly_and_collect(flyer)
        # Setup for many batches
        many_batches = RepeatedTrigger(
            num=num_frames,
            width=exposure,
            deadtime=deadtime,
            repeats=(num - 1),
            period=abs((stop - start) / (rate / 60)) / (num - 1),
        )
        yield from bps.mv(flyer, many_batches)
        # Then start flying, collecting roughly every step
        linkam_group = group_uuid("linkam")
        yield from bps.abs_set(linkam, stop, group=linkam_group, wait=False)
        # Collect constantly
        yield from fly_and_collect(flyer)
        # Make sure linkam has finished
        yield from bps.wait(group=linkam_group)
    else:
        temps = np.linspace(start, stop, num)
        for temp in temps:
            yield from bps.mv(linkam, temp, flyer, one_batch)
            # Collect at each step
            yield from fly_and_collect(flyer)
