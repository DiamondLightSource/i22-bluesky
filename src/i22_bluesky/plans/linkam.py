from pathlib import Path
from typing import Any, Dict, Optional

import bluesky.preprocessors as bpp
import bluesky.plan_stubs as bps
from dls_bluesky_core.core import MsgGenerator
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import (
    HardwareTriggeredFlyable,
    SameTriggerDetectorGroupLogic,
    StandardDetector,
)
from ophyd_async.panda import PandA

from i22_bluesky.util.settings import load_saxs_linkam_settings

from i22_bluesky.panda.fly_scanning import PandARepeatedTriggerLogic
from i22_bluesky.stubs.linkam import scan_linkam

# TODO: Define args as tuple (aim, step, rate) or dataclass?

# TODO: Define generic plan that follows N temperature sections?
# Rose TODO: use inject from dls-bluesky-core (ask Joseph)
def linkam_plan(
    saxs: StandardDetector,
    # waxs: StandardDetector,
    tetramm: StandardDetector,
    linkam: Linkam3,
    panda: PandA,
    start_temp: float,
    cool_temp: float,
    cool_step: float,
    cool_rate: float,
    heat_temp: float,
    heat_step: float,
    heat_rate: float,
    num_frames: int,
    exposure: float,
    metadata: Optional[Dict[str, Any]] = None,
) -> MsgGenerator:
    """Cool in steps, then heat constantly, taking collections of num_frames each time::

                      _             __ heat_temp
                     / \\           /
        cool_step_______\\__       /
                           \\     /
                  cool_temp \\__ /
        exposures        xx  xx   xx    num_frames=2 each time

    Fast shutter will be opened for each group of exposures


    Args:
        saxs: saxs detector
        waxs: waxs detector
        linkam: Linkam temperature stage
        panda: PandA for controlling flyable motion
        start_temp: initial temperature to reach before starting experiment
        cool_temp: target end temp for cooling stage
        cool_step: temperature step dT after each to perform scan
        cool_rate: rate of change of temperature with time, dT/dt
        heat_temp: target end temp for heating stage
        heat_step: temperature step dT after each to perform scan
        heat_rate: rate of change of temperature with time, dT/dt
        num_frames: number of frames to take at each point in temperature
        exposure: exposure time of detectors
        metadata: metadata: Key-value metadata to include in exported data,
            defaults to None.

    Returns:
        MsgGenerator: Plan

    Yields:
        Iterator[MsgGenerator]: Bluesky messages
    """
    plan_args = {
        "saxs": repr(saxs),  # TODO: can we take [detectors] and assume saxs is [0]?
        # "waxs": repr(waxs),
        "tetramm": repr(tetramm),
        "linkam": repr(linkam),
        "panda": repr(panda),
        "start_temp": start_temp,
        "cool_temp": cool_temp,
        "cool_step": cool_step,
        "cool_rate": cool_rate,
        "heat_temp": heat_temp,
        "heat_step": heat_step,
        "heat_rate": heat_rate,
        "num_frames": num_frames,
        "exposure": exposure,
    }
    #dets = [saxs, waxs]
    dets = [saxs, tetramm]
    flyer = HardwareTriggeredFlyable(
        SameTriggerDetectorGroupLogic(
            [det.controller for det in dets],
            [det.writer for det in dets],
        ),
        PandARepeatedTriggerLogic(panda.seq[1], shutter_time=0.004),
        # TODO: Should this include config_with_temperature_stamping?
        configuration_signals=[],
        # TODO: Or else where should this be/where does it come from?
        # settings={saxs: config_with_temperature_stamping},
        # Or maybe a different object?
        name="flyer",
    )
    deadtime = max(det.controller.get_deadtime(exposure) for det in dets)
    _md = {
        "detectors": [det.name for det in dets],
        "plan_args": plan_args,
        # TODO: Can we pass dimensional hint? motors? shape?
        "hints": {},
    }
    _md.update(metadata or {})

    @bpp.stage_decorator([flyer])
    @bpp.run_decorator(md=_md)
    def inner_linkam_plan():
        yield from load_saxs_linkam_settings(saxs, Path("/dls_sw/p38/software/blueapi/scratch/nxattributes"))
        # Step down at the cool rate
        yield from scan_linkam(
            linkam=linkam,
            flyer=flyer,
            start=start_temp,
            stop=cool_temp,
            step=cool_step,
            rate=cool_rate,
            exposure=exposure,
            deadtime=deadtime,
            num_frames=num_frames,
            fly=False,
        )
        # Fly up at the heat rate
        yield from scan_linkam(
            linkam=linkam,
            flyer=flyer,
            start=cool_temp,
            stop=heat_temp,
            step=heat_step,
            rate=heat_rate,
            exposure=exposure,
            deadtime=deadtime,
            num_frames=num_frames,
            fly=True,
        )

    rs_uid = yield from inner_linkam_plan()
    return rs_uid
