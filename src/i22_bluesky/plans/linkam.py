from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.preprocessors import finalize_decorator
from dls_bluesky_core.core import MsgGenerator, inject
from dodal.devices.linkam3 import Linkam3
from dodal.devices.tetramm import free_tetramm
from ophyd_async.core import (
    HardwareTriggeredFlyable,
    SameTriggerDetectorGroupLogic,
    StandardDetector,
)
from ophyd_async.panda import PandA

from i22_bluesky.panda.fly_scanning import PandARepeatedTriggerLogic, RepeatedTrigger
from i22_bluesky.stubs import load_device, scan_linkam, send_triggers
from i22_bluesky.util.settings import (
    load_pilatus_settings,
    load_tetramm_linkam_settings,
)

# TODO: Define args as tuple (aim, step, rate) or dataclass?

# TODO: Define generic plan that follows N temperature sections?
XML_PATH = Path("/dls_sw/i22/software/blueapi/scratch/nxattributes")


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
    fly_down: bool = False,
    fly_up: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
    saxs: StandardDetector = inject("saxs"),
    waxs: StandardDetector = inject("waxs"),
    tetramm1: StandardDetector = inject("i0"),
    tetramm2: StandardDetector = inject("it"),
    linkam: Linkam3 = inject("linkam"),
    panda: PandA = inject("panda-01"),
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
    dets = [saxs, waxs, tetramm1, tetramm2]
    plan_args = {
        "dets": [device.name for device in dets],
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

    yield from load_device(panda)
    yield from load_device(linkam)

    for det in dets:
        yield from load_device(det)

    free_first_tetramm = partial(free_tetramm, tetramm1)
    free_second_tetramm = partial(free_tetramm, tetramm2)

    tetramm1.controller.minimum_frame_time = exposure
    tetramm2.controller.minimum_frame_time = exposure

    # at the end of the plan, start the tetramms in freerun mode so their diode values
    # constantly update.
    @finalize_decorator(free_first_tetramm)
    @finalize_decorator(free_second_tetramm)
    @bpp.stage_decorator([flyer])
    @bpp.run_decorator(md=_md)
    def inner_linkam_plan():
        yield from load_pilatus_settings(saxs, waxs, XML_PATH)
        yield from load_tetramm_linkam_settings(linkam, tetramm1, XML_PATH)
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
            fly=fly_down,
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
            fly=fly_up,
        )

    rs_uid = yield from inner_linkam_plan()
    return rs_uid


def one_shot_linkam(
    temp: float,
    exposure: float,
    num_frames: int,
    ramp_rate: float = 50,
    metadata: Optional[Dict[str, Any]] = None,
    fly: bool = False,
    saxs: StandardDetector = inject("saxs"),
    waxs: StandardDetector = inject("waxs"),
    tetramm1: StandardDetector = inject("i0"),
    tetramm2: StandardDetector = inject("it"),
    linkam: Linkam3 = inject("linkam"),
    panda: PandA = inject("panda-01"),
) -> MsgGenerator:
    dets = [saxs, waxs, tetramm1, tetramm2]
    plan_args = {
        "dets": [device.name for device in dets],
        "temp": temp,
        "ramnp_rate": ramp_rate,
        "num_frames": num_frames,
        "exposure": exposure,
    }
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

    yield from load_device(panda)
    yield from load_device(linkam)

    for det in dets:
        yield from load_device(det)

    free_first_tetramm = partial(free_tetramm, tetramm1)
    free_second_tetramm = partial(free_tetramm, tetramm2)

    tetramm1.controller.minimum_frame_time = exposure
    tetramm2.controller.minimum_frame_time = exposure

    @finalize_decorator(free_first_tetramm)
    @finalize_decorator(free_second_tetramm)
    @bpp.stage_decorator([flyer])
    @bpp.run_decorator(md=_md)
    def inner_plan():
        yield from load_pilatus_settings(saxs, waxs, XML_PATH)
        yield from load_tetramm_linkam_settings(linkam, tetramm1, XML_PATH)
        yield from scan_linkam(
            linkam=linkam,
            flyer=flyer,
            start=temp,
            stop=temp,
            step=1,
            rate=ramp_rate,
            exposure=exposure,
            deadtime=deadtime,
            num_frames=num_frames,
            fly=fly,
        )

    rs_id = yield from inner_plan()
    return rs_id


"""
100 Hz for 60s = 6000 frames
 tr 1                                      time resolution 2
|------|------|------|------|------|------|------------------| .. etc.
 ==========    ===    ===    ===    ===    ===       -> exposures. 

one_batch = RepeatedTrigger(num=100*60, width=exposure, deadtime=deadtime)
second_Batch = RepeatedTrigger(num=100, width, deadtime, repeats (no. of minutes..), period (minute))
"""


def rapid_cooling(
    exposure: float,  # time resolution. i.e. for 100Hz this is 0.01.
    cool_temp: float = 20,
    initial_sleep: float = 60 * 10,
    metadata: Optional[Dict[str, Any]] = None,
    saxs: StandardDetector = inject("saxs"),
    waxs: StandardDetector = inject("waxs"),
    tetramm1: StandardDetector = inject("i0"),
    tetramm2: StandardDetector = inject("it"),
    linkam: Linkam3 = inject("linkam"),
    panda: PandA = inject("panda-01"),
) -> MsgGenerator:
    """Starting at a temperature, fly to another one, taking num_frames for the temperatures (inclusive)"""
    dets = [saxs, waxs, tetramm1, tetramm2]
    plan_args = {
        "dets": [device.name for device in dets],
        "cool_temp": cool_temp,
        "exposure": exposure,
    }
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
        "exposure": exposure,
        # TODO: Can we pass dimensional hint? motors? shape?
        "hints": {},
    }
    _md.update(metadata or {})

    yield from load_device(panda)
    yield from load_device(linkam)

    for det in dets:
        yield from load_device(det)

    free_first_tetramm = partial(free_tetramm, tetramm1)
    free_second_tetramm = partial(free_tetramm, tetramm2)

    tetramm1.controller.minimum_frame_time = exposure
    tetramm2.controller.minimum_frame_time = exposure

    one_batch = RepeatedTrigger(
        num=int((1 / exposure) * 60), width=exposure, deadtime=deadtime
    )

    @finalize_decorator(free_first_tetramm)
    @finalize_decorator(free_second_tetramm)
    @bpp.stage_decorator([flyer])
    @bpp.run_decorator(md=_md)
    def inner_plan():
        yield from load_pilatus_settings(saxs, waxs, XML_PATH)
        yield from load_tetramm_linkam_settings(linkam, tetramm1, XML_PATH)

        yield from bps.mv(linkam, 80)

        yield from bps.sleep(initial_sleep)

        yield from bps.mv(linkam.ramp_rate, 100)

        yield from bps.mv(linkam, cool_temp, flyer, one_batch)
        yield from send_triggers(flyer, exposure, deadtime)

    rs_id = yield from inner_plan()
    return rs_id


# now make another one, which steps down, waits for a time, then takes images.


def step_and_wait(
    start_temp: float,
    cool_temp: float,
    cool_rate: float,
    cool_step: float,
    num_frames: float,
    sleep_for: float,
    exposure: float,
    metadata: Optional[Dict[str, Any]] = None,
    saxs: StandardDetector = inject("saxs"),
    waxs: StandardDetector = inject("waxs"),
    tetramm1: StandardDetector = inject("i0"),
    tetramm2: StandardDetector = inject("it"),
    linkam: Linkam3 = inject("linkam"),
    panda: PandA = inject("panda-01"),
) -> MsgGenerator:
    dets = [saxs, waxs, tetramm1, tetramm2]
    plan_args = {
        "dets": [device.name for device in dets],
        "start_temp": start_temp,
        "cool_temp": cool_temp,
        "cool_step": cool_step,
        "cool_rate": cool_rate,
        "num_frames": num_frames,
        "sleep_for": sleep_for,
        "exposure": exposure,
    }
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

    yield from load_device(panda)
    yield from load_device(linkam)

    for det in dets:
        yield from load_device(det)

    free_first_tetramm = partial(free_tetramm, tetramm1)
    free_second_tetramm = partial(free_tetramm, tetramm2)

    tetramm1.controller.minimum_frame_time = exposure
    tetramm2.controller.minimum_frame_time = exposure

    @finalize_decorator(free_first_tetramm)
    @finalize_decorator(free_second_tetramm)
    @bpp.stage_decorator([flyer])
    @bpp.run_decorator(md=_md)
    def inner_linkam_plan():
        yield from load_pilatus_settings(saxs, waxs, XML_PATH)
        yield from load_tetramm_linkam_settings(linkam, tetramm1, XML_PATH)
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
            sleep=sleep_for,
        )

    rs_uid = yield from inner_linkam_plan()
    return rs_uid
