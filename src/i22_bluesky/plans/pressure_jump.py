from typing import Any

import bluesky.plans as bp
import bluesky.preprocessors as bpp
from bluesky.protocols import Readable
from bluesky.utils import MsgGenerator
from dodal.devices.tetramm import TetrammDetector
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import (
    Device,
    StandardDetector,
    StandardFlyer,
)
from ophyd_async.fastcs.panda import HDFPanda, StaticSeqTableTriggerLogic
from ophyd_async.plan_stubs import (
    fly_and_collect,
)

from i22_bluesky.plans.stopflow import (
    DEFAULT_BASELINE_MEASUREMENTS,
    raise_for_minimum_exposure_times,
)
from i22_bluesky.stubs.pressure_jump import prepare_seq_table_flyer_and_det
from i22_bluesky.util.baseline import (
    DEFAULT_DETECTORS,
    DEFAULT_PANDA,
    DEFAULT_PRESSURE_CELL,
)
from i22_bluesky.util.settings import load_device, save_device

_PLAN_NAME = "pressure_jump"


def save_device_for_pressure_jump(device: Device = DEFAULT_PANDA) -> MsgGenerator:
    yield from save_device(device, _PLAN_NAME)


@attach_data_session_metadata_decorator()
def check_detectors_for_pressure_jump(
    num_frames: int = 1,
    devices: set[Readable] = DEFAULT_DETECTORS | DEFAULT_BASELINE_MEASUREMENTS,
) -> MsgGenerator:
    """
    Take a reading from all devices that are used in the
    pressure jump plan by default
    """

    # Tetramms do not support software triggering
    software_triggerable_devices = {
        device for device in devices if not isinstance(device, TetrammDetector)
    }
    yield from bp.count(
        software_triggerable_devices,
        num=num_frames,
    )


def pressure_jump(
    start_pressure: float,
    end_pressure: float,
    duration: float,
    exposure: float,
    pre_jump_frames: int = 1,
    post_jump_frames: int = 1,
    shutter_time: float = 4e-3,
    metadata: dict[str, Any] | None = None,
    baseline: set[Readable] = DEFAULT_BASELINE_MEASUREMENTS,
    detectors: set[StandardDetector] = DEFAULT_DETECTORS,
    pressure_cell: StandardDetector = DEFAULT_PRESSURE_CELL,
    panda: HDFPanda = DEFAULT_PANDA,
) -> MsgGenerator:
    """
    Perform a pressure jump measurement
    see a detailed description in
    https://github.com/DiamondLightSource/i22-bluesky/issues/79

    Args:
        panda: PandA for controlling flyable motion.
        detectors: A set of detectors that will be collected.
        baseline: A set of devices to be read at the start and end of the plan
            in a stream names baseline.
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
    # Check that all detectors supplied can actually go as
    # fast as requested
    raise_for_minimum_exposure_times(exposure, detectors)

    stream_name = "main"
    flyer = StandardFlyer(StaticSeqTableTriggerLogic(panda.seq[1]))
    devices = {flyer, panda} | detectors | baseline
    plan_args = {
        "start_pressure": start_pressure,
        "end_pressure": end_pressure,
        "duration": duration,
        "exposure": exposure,
        "panda": panda.name,
        "detectors": {d.name for d in detectors},
        "baseline": {d.name for d in baseline},
    }
    _md = {
        "detectors": {d.name for d in detectors},
        "motors": {pressure_cell.name},
        "plan_args": plan_args,
        "hints": {},
    }
    _md.update(metadata or {})

    for device in detectors:
        yield from load_device(device, _PLAN_NAME)

    @bpp.baseline_decorator(baseline)
    @attach_data_session_metadata_decorator()
    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_plan():
        yield from load_device(panda, _PLAN_NAME)
        yield from prepare_seq_table_flyer_and_det(
            flyer=flyer,
            detectors=detectors,
            pre_jump_frames=pre_jump_frames,
            post_jump_frames=post_jump_frames,
            exposure=exposure,
            shutter_time=shutter_time,
        )
        yield from fly_and_collect(
            stream_name=stream_name,
            detectors=detectors,
            flyer=flyer,
        )

    rs_uid = yield from inner_plan()
    return rs_uid
