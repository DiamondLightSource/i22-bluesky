from time import time
from typing import List, Optional, Protocol, runtime_checkable

import bluesky.plan_stubs as bps
import numpy as np
from bluesky.protocols import Collectable, Flyable
from dodal.common.coordination import group_uuid
from dodal.common.maths import step_to_num
from dodal.common.types import MsgGenerator
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core.flyer import HardwareTriggeredFlyable

from i22_bluesky.panda.fly_scanning import RepeatedTrigger


@runtime_checkable
class CollectableFlyable(Collectable, Flyable, Protocol):
    """
    A Device which implements both the Collectable and Flyable protocols.
    i.e., a device which can be set off, then polled repeatedly to construct documents
    with the data it has collected so far. A typical pattern for "hardware" scans
    """


def fly_and_collect(
    flyer: Flyable,
    devices: List[CollectableFlyable],
    flush_period: float = 0.5,
    timeout: float = 7_200,
    checkpoint_every_collect: bool = False,
    stream_name: str = "primary",
) -> MsgGenerator:
    """Fly a flyer which controls a series of Collectable devices, then repeatedly
    collect from the controlled devices.

    This plan may need to be called in succession in order to e.g., set up a flyer
    to send triggers multiple times and collect data. For such a use case checkpoint after each collect.

    Args:
        flyer (Flyable): ophyd-async device which implements Flyable
        devices (List[Collectable & Flyable]): devices controlled by the Flyer which produce data
        flush_period (float): How often (in seconds) to check if flyer.complete has finished.
                              Defaults to 0.5
        timeout (float): period after which the plan should be automatically aborted for taking too long and assumed to be stuck. Default 7200 seconds (2 hours)
        checkpoint_every_collect (bool): whether or not to checkpoint after
                                        collect has been called. Defaults to
                                         False.
        stream_name (str): name of the stream to collect from. Defaults to "primary".


    Returns:
        MsgGenerator: Plan

    Yields:
        Iterator[MsgGenerator]: Bluesky messages
    """

    yield from bps.kickoff(flyer)
    for device in devices:
        yield from bps.kickoff(device)

    guid = group_uuid("complete")

    yield from bps.complete(flyer, wait=False, group=guid)
    for device in devices:
        yield from bps.complete(device, wait=False, group=guid)

    done = False
    start_time = time.time()
    while not done:
        if time.time() - start_time > timeout:
            raise TimeoutError
        try:
            yield from bps.wait(group=guid, timeout=flush_period)
        except TimeoutError:
            pass
        else:
            done = True
        yield from bps.collect(
            *devices, stream=True, return_payload=False, name=stream_name
        )
        if checkpoint_every_collect:
            yield from bps.checkpoint()


# TODO: Make non-flyer signature to allow non-flying with non-flying device?
def scan_linkam(
    linkam: Linkam3,
    flyer: HardwareTriggeredFlyable,
    start: float,
    stop: float,
    step: float,
    rate: float,  # deg C/min
    exposure: float,
    deadtime: float,
    num_frames: int,
    fly=False,
    detectors: Optional[List[Flyable]] = None,
):
    one_batch = RepeatedTrigger(num=num_frames, width=exposure, deadtime=deadtime)
    start, stop, num = step_to_num(start, stop, step)
    yield from bps.mv(linkam.ramp_rate, rate)
    if fly:
        # Do a single batch to start
        yield from bps.mv(linkam, start)
        yield from bps.prepare(flyer, one_batch, wait=True)
        guid = group_uuid("prepare")
        for d in detectors:
            yield from bps.prepare(d, flyer.trigger_info, group=guid)
        yield from bps.wait(guid)
        yield from fly_and_collect(flyer, detectors=detectors)
        # Setup for many batches
        many_batches = RepeatedTrigger(
            num=num_frames,
            width=exposure,
            deadtime=deadtime,
            repeats=(num - 1),
            period=abs((stop - start) / (rate / 60)) / (num - 1),
        )
        yield from bps.prepare(flyer, many_batches)
        # Then start flying, collecting roughly every step
        linkam_group = group_uuid("linkam")
        yield from bps.abs_set(linkam, stop, group=linkam_group, wait=False)
        # Collect constantly
        yield from fly_and_collect(flyer, detectors=detectors)
        # Make sure linkam has finished
        yield from bps.wait(group=linkam_group)
    else:
        temps = np.linspace(start, stop, num)
        for temp in temps:
            yield from bps.mv(linkam, temp)
            yield from bps.prepare(flyer, one_batch)
            # Collect at each step
            yield from fly_and_collect(flyer, detectors=detectors)
