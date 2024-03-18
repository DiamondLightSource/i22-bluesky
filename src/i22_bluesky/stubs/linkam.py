from typing import List

import bluesky.plan_stubs as bps
import numpy as np
from dodal.common.coordination import group_uuid
from dodal.common.maths import step_to_num
from dodal.common.types import MsgGenerator
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core.flyer import HardwareTriggeredFlyable

from i22_bluesky.common.types import CollectableFlyable
from i22_bluesky.panda.fly_scanning import RepeatedTrigger
from i22_bluesky.stubs.fly import fly_and_collect


# TODO: Make non-flyer signature to allow non-flying with non-flying device?
def scan_linkam(
    flyer: HardwareTriggeredFlyable[RepeatedTrigger],
    devices: List[CollectableFlyable],
    linkam: Linkam3,
    start: float,
    stop: float,
    step: float,
    rate: float,  # deg C/min
    exposure: float,
    deadtime: float,
    num_frames: int,
    fly=False,
) -> MsgGenerator:
    # Take num_frames from each device once
    one_batch = RepeatedTrigger(num=num_frames, width=exposure, deadtime=deadtime)

    start, stop, num = step_to_num(start, stop, step)
    # Take num_frames from each devices periodically
    many_batches = RepeatedTrigger(
        num=num_frames,
        width=exposure,
        deadtime=deadtime,
        repeats=num - 1,
        period=abs((stop - start) / (rate / 60)) / (num - 1),
    )

    def prepare_all_with_trigger(trigger: RepeatedTrigger) -> MsgGenerator:
        yield from bps.prepare(flyer, trigger, wait=True)
        guid = group_uuid("prepare")
        for device in devices:
            yield from bps.prepare(device, flyer.trigger_info, group=guid)
        yield from bps.wait(guid)

    yield from bps.mv(linkam.ramp_rate, rate)
    if fly:
        # Do a single batch to start
        yield from bps.mv(linkam, start)
        yield from prepare_all_with_trigger(one_batch)
        yield from fly_and_collect(flyer, devices)

        # Setup for many batches
        yield from prepare_all_with_trigger(many_batches)
        # Then start flying, collecting roughly every step
        linkam_group = group_uuid("linkam")
        yield from bps.abs_set(linkam, stop, group=linkam_group, wait=False)
        # Collect constantly
        yield from fly_and_collect(flyer, devices=devices)
        # Make sure linkam has finished
        yield from bps.wait(group=linkam_group)
    else:
        temps = np.linspace(start, stop, num)
        for temp in temps:
            yield from bps.mv(linkam, temp)
            yield from bps.prepare(flyer, one_batch, wait=True)
            # Collect at each step
            yield from fly_and_collect(flyer, devices=devices)
