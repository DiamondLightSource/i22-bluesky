from functools import partial
from pathlib import Path
from typing import Any, Dict, Optional

import bluesky.preprocessors as bpp
from bluesky.preprocessors import finalize_decorator
from dls_bluesky_core.core import MsgGenerator, inject
from dodal.devices.linkam3 import Linkam3
from dodal.devices.tetramm import TetrammDetector
from dodal.plans.data_session_metadata import attach_session_metadata_decorator
from ophyd_async.core import HardwareTriggeredFlyable, StandardDetector
from ophyd_async.panda import HDFPanda, StaticSeqTableTriggerLogic

from i22_bluesky.stubs import load
from i22_bluesky.stubs.linkam import scan_linkam
from i22_bluesky.util.settings import load_saxs_linkam_settings, load_waxs_settings

# TODO: Define args as tuple (aim, step, rate) or dataclass?


@attach_session_metadata_decorator()
def linkam_plan(
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
    saxs: StandardDetector = inject("saxs"),
    waxs: StandardDetector = inject("waxs"),
    tetramm1: StandardDetector = inject("i0"),
    tetramm2: StandardDetector = inject("it"),
    linkam: Linkam3 = inject("linkam"),
    panda: HDFPanda = inject("panda-01"),
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
    flyer = HardwareTriggeredFlyable(StaticSeqTableTriggerLogic(panda.seq[1]))
    detectors = [saxs, waxs, tetramm1, tetramm2]

    plan_args = {
        "start_temp": start_temp,
        "cool_temp": cool_temp,
        "cool_step": cool_step,
        "cool_rate": cool_rate,
        "heat_temp": heat_temp,
        "heat_step": heat_step,
        "heat_rate": heat_rate,
        "num_frames": num_frames,
        "exposure": exposure,
        "saxs": repr(saxs),
        "waxs": repr(waxs),
        "tetramm1": repr(tetramm1),
        "tetramm2": repr(tetramm2),
        "linkam": repr(linkam),
        "panda": repr(panda),
    }
    _md = {
        "detectors": [device.name for device in detectors],
        "motors": [linkam.name],
        "plan_args": plan_args,
        # TODO: Can we pass dimensional hint? motors? shape?
        "hints": {},
    }
    _md.update(metadata or {})

    yield from load(detectors + [panda, linkam], "linkam_plan")

    devices = [flyer] + detectors

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_linkam_plan():
        yield from load_saxs_linkam_settings(linkam, saxs, XML_PATH)
        yield from load_waxs_settings(waxs, XML_PATH)
        # Step down at the cool rate
        yield from scan_linkam(
            linkam=linkam,
            flyer=flyer,
            detectors=detectors,
            start=start_temp,
            stop=cool_temp,
            step=cool_step,
            rate=cool_rate,
            num_frames=num_frames,
            exposure=exposure,
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
            num_frames=num_frames,
            exposure=exposure,
            fly=True,
        )

    rs_uid = yield from inner_linkam_plan()
    return rs_uid
