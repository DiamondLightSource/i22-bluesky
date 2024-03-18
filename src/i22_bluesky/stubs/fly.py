from time import time
from typing import List, TypeVar

import bluesky.plan_stubs as bps
from bluesky.protocols import Flyable
from dodal.common.coordination import group_uuid
from dodal.common.types import MsgGenerator
from ophyd_async.core.flyer import HardwareTriggeredFlyable

from i22_bluesky.common.types import CollectableFlyable

T = TypeVar("T")


def prepare_all_with_trigger(
    flyer: HardwareTriggeredFlyable[T], devices: List[CollectableFlyable], trigger: T
) -> MsgGenerator:
    yield from bps.prepare(flyer, trigger, wait=True)
    guid = group_uuid("prepare")
    for device in devices:
        yield from bps.prepare(device, flyer.trigger_info, group=guid)
    yield from bps.wait(guid)


def fly_and_collect(
    flyer: Flyable,
    devices: List[CollectableFlyable],
    flush_period: float = 0.5,
    timeout: float = 7_200,
    checkpoint_every_collect: bool = False,
) -> MsgGenerator:
    """Fly a flyer which controls a series of Collectable devices, then repeatedly
    collect from the controlled devices.

    Args:
        flyer (Flyable): Device which controls the triggering of collectable devices
        devices (List[CollectableFlyable]): devices controlled by the Flyer which produce data
        flush_period (float): How often (in seconds) to readout the devices.
                              Default 0.5
        timeout (float): Period (in seconds) after which the plan may be aborted for
            taking too long and assumed to be stuck.
            Default 7200 (2 hours)
        checkpoint_every_collect (bool): Whether to checkpoint after each Collect. Default False
        stream_name (str): Name of the stream to collect from. Default "primary".


    Returns:
        MsgGenerator: Plan

    Yields:
        Iterator[MsgGenerator]: Bluesky messages
    """

    yield from bps.kickoff(flyer)
    for device in devices:
        yield from bps.kickoff(device)

    guid = group_uuid("complete")

    yield from bps.complete(flyer, group=guid)
    for device in devices:
        yield from bps.complete(device, group=guid)

    done = False
    start_time = time()
    while not done:
        if time() - start_time > timeout:
            raise TimeoutError
        try:
            yield from bps.wait(group=guid, timeout=flush_period)
        except TimeoutError:
            pass
        else:
            done = True
        yield from bps.collect(
            *devices, stream=True, return_payload=False, name="primary"
        )
        if checkpoint_every_collect:
            yield from bps.checkpoint()
