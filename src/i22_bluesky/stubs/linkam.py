import bluesky.plan_stubs as bps
import numpy as np
from dodal.common.coordination import group_uuid
from dodal.common.maths import step_to_num
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import StandardDetector
from ophyd_async.core.flyer import HardwareTriggeredFlyable
from ophyd_async.plan_stubs import (
    fly_and_collect,
    prepare_static_seq_table_flyer_and_detectors_with_same_trigger,
)


def scan_linkam(
    linkam: Linkam3,
    flyer: HardwareTriggeredFlyable,
    detectors: set[StandardDetector],
    start: float,
    stop: float,
    step: float,
    rate: float,  # deg C/min
    num_frames: int,
    exposure: float,
    fly=False,
):
    stream_name = "main"
    shutter_time = 0.004
    start, stop, num = step_to_num(start, stop, step)
    yield from bps.mv(linkam.ramp_rate, rate)
    if fly:
        # Do a single batch to start
        yield from bps.mv(linkam, start)
        yield from prepare_static_seq_table_flyer_and_detectors_with_same_trigger(
            flyer=flyer,
            detectors=detectors,
            number_of_frames=num_frames,
            exposure=exposure,
            shutter_time=shutter_time,
        )
        yield from fly_and_collect(
            stream_name=stream_name,
            flyer=flyer,
            detectors=detectors,
        )
        # Setup for many batches
        # Then start flying, collecting roughly every step
        linkam_group = group_uuid("linkam")
        yield from bps.abs_set(linkam, stop, group=linkam_group, wait=False)
        # Collect constantly
        yield from prepare_static_seq_table_flyer_and_detectors_with_same_trigger(
            flyer=flyer,
            detectors=detectors,
            number_of_frames=num_frames,
            exposure=exposure,
            shutter_time=shutter_time,
            repeats=(num_frames - 1),
            period=abs((stop - start) / (rate / 60)) / (num - 1),
        )
        yield from fly_and_collect(
            stream_name=stream_name,
            flyer=flyer,
            detectors=detectors,
        )
        # Make sure linkam has finished
        yield from bps.wait(group=linkam_group)
    else:
        temps = np.linspace(start, stop, num)
        for temp in temps:
            yield from bps.mv(linkam, temp)
            # Collect at each step
            yield from prepare_static_seq_table_flyer_and_detectors_with_same_trigger(
                flyer=flyer,
                detectors=detectors,
                number_of_frames=num_frames,
                exposure=exposure,
                shutter_time=shutter_time,
            )
            yield from fly_and_collect(
                stream_name=stream_name,
                flyer=flyer,
                detectors=detectors,
            )
