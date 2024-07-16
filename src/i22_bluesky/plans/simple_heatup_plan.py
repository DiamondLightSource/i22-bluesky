from typing import List
from dls_bluesky_core.core import group_uuid, step_to_num

from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional

import bluesky.preprocessors as bpp
from bluesky.preprocessors import finalize_decorator
from dls_bluesky_core.core import MsgGenerator, inject
from dodal.devices.linkam3 import Linkam3
from dodal.devices.tetramm import TetrammDetector
from dodal.plans.data_session_metadata import attach_data_session_metadata_decorator
from ophyd_async.core import HardwareTriggeredFlyable, StandardDetector
from ophyd_async.panda import HDFPanda, StaticSeqTableTriggerLogic

from i22_bluesky.stubs import load
from i22_bluesky.stubs.linkam import scan_linkam
from i22_bluesky.util.settings import load_saxs_linkam_settings, load_waxs_settings

from pathlib import Path
from dodal.log import LOGGER
import bluesky.plan_stubs as bps
import numpy as np
from dls_bluesky_core.core import group_uuid, step_to_num, MsgGenerator, inject
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import StandardDetector
from ophyd_async.core.flyer import HardwareTriggeredFlyable
from ophyd_async.plan_stubs import (
    fly_and_collect,
    prepare_static_seq_table_flyer_and_detectors_with_same_trigger,
)

XML_PATH = Path("/dls_sw/i22/software/blueapi/scratch/nxattributes")

@attach_data_session_metadata_decorator()
def simple_heatup_plan(
    detector: StandardDetector= inject("saxs"),
    start: float=180.0,
    stop: float=185.0,
    step: float=0.2,
    rate: float=10.0,  # deg C/min
    num_frames: int=1,
    exposure: float=0.1,
    linkam: Linkam3 = inject("linkam"),
    panda: HDFPanda = inject("panda1"),
    fly: bool = False,
    
)-> MsgGenerator:

    devices = [detector , linkam]
    flyer = HardwareTriggeredFlyable(StaticSeqTableTriggerLogic(panda.seq[1]))
    
    yield from load_saxs_linkam_settings(linkam, detector, XML_PATH)

    @bpp.stage_decorator(devices)
    @bpp.run_decorator()
    def inner_plan():
        stream_name = "main"
        shutter_time = 0.004
        LOGGER.log(start, stop, num)
        start, stop, num = step_to_num(start, stop, step)
        LOGGER.log("step is working")
        LOGGER.log(start, stop, num)
        yield from bps.mv(linkam.ramp_rate, rate)
        yield from bps.mv(linkam, start)
        LOGGER.log("start linkam works")
        yield from prepare_static_seq_table_flyer_and_detectors_with_same_trigger(
            flyer=flyer,
            detectors=detectors,
            number_of_frames=num_frames,
            exposure=exposure,
            shutter_time=shutter_time,
        )
        LOGGER.log("tryingf to do fly and collect")
        yield from fly_and_collect(
            stream_name=stream_name,
            flyer=flyer,
            detectors=detectors,
        )
        LOGGER.log(" fly and collect works")
        # Setup for many batches
        # Then start flying, collecting roughly every step
        linkam_group = group_uuid("linkam")
        yield from bps.abs_set(linkam, stop, group=linkam_group, wait=False)
        # Collect constantly
        LOGGER.log(" collecting constantly")
        yield from prepare_static_seq_table_flyer_and_detectors_with_same_trigger(
            flyer=flyer,
            detectors=detectors,
            number_of_frames=num_frames,
            exposure=exposure,
            shutter_time=shutter_time,
            repeats=(num_frames - 1),
            period=abs((stop - start) / (rate / 60)) / (num - 1),
        )
        LOGGER.log(" final collection")
        yield from fly_and_collect(
            stream_name=stream_name,
            flyer=flyer,
            detectors=detectors,
        )
        # Make sure linkam has finished
        yield from bps.wait(group=linkam_group)

    yield from inner_plan()
