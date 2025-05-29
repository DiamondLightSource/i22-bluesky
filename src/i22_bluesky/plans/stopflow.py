# Stop flow experiment

# The experiment involves a liquid sample intersecting and flowing laterally to the
# beam.
# The beam passes through the flowing liquid and scatters onto a detector.
# The flow is controlled by a proprietary rig that allows the user to request a
# "stop flow".
# At the moment the flow stops, the rig sends out a pulse to the panda, which can
# then trigger the detector.

# A single pulse goes into the panda and many pulses come out via a sequencer table.
# The table can specify X sets of Y pulses at Z hertz.

# Frames may also be collected before waiting for the trigger.

# As such the implementation is:
# start acquisition -> acquire n frames -> wait for trigger -> acquire m frames
# where n can be 0.

from typing import Any

import bluesky.plans as bp
import bluesky.preprocessors as bpp
from bluesky.protocols import Readable
from bluesky.utils import MsgGenerator
from dodal.devices.tetramm import TetrammDetector
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import (
    StandardDetector,
    StandardFlyer,
)
from ophyd_async.fastcs.panda import (
    HDFPanda,
    StaticSeqTableTriggerLogic,
)
from ophyd_async.plan_stubs import fly_and_collect

from i22_bluesky.stubs.stopflow import (
    prepare_seq_table_flyer_and_det,
    raise_for_minimum_exposure_times,
)
from i22_bluesky.util.baseline import (
    DEFAULT_BASELINE_MEASUREMENTS,
    DEFAULT_DETECTORS,
    DEFAULT_PANDA,
    FAST_DETECTORS,
)
from i22_bluesky.util.settings import load_device, save_device

_PLAN_NAME = "stopflow"


# various testing plans
@attach_data_session_metadata_decorator()
def check_detectors_for_stopflow(
    num_frames: int = 1,
    devices: set[Readable] = DEFAULT_DETECTORS | DEFAULT_BASELINE_MEASUREMENTS,
) -> MsgGenerator:
    """
    Take a reading from all devices that are used in the
    stopflow plan by default
    """

    # Tetramms do not support software triggering
    software_triggerable_devices = {
        device for device in devices if not isinstance(device, TetrammDetector)
    }
    yield from bp.count(
        tuple(software_triggerable_devices),
        num=num_frames,
    )


def check_stopflow_assembly(
    panda: HDFPanda = DEFAULT_PANDA,
    detectors: set[StandardDetector] = DEFAULT_DETECTORS,
    baseline: set[Readable] = DEFAULT_BASELINE_MEASUREMENTS,
) -> MsgGenerator:
    """
    Simplified version of the stopflow plan that should catch most
    wiring/assembly/detector setup errors, does not require triggering a stop flow,
    that can be tested with the main plan.
    """

    yield from stopflow(
        exposure=0.1,
        post_stop_frames=0,
        pre_stop_frames=10,
        shutter_time=4e-3,
        panda=panda,
        detectors=detectors,
        baseline=baseline,
    )


def check_stopflow_experiment(
    panda: HDFPanda = DEFAULT_PANDA,
    detectors: set[StandardDetector] = DEFAULT_DETECTORS,
    baseline: set[Readable] = DEFAULT_BASELINE_MEASUREMENTS,
) -> MsgGenerator:
    """
    Full test of stopflow experiment functionality with sensible values
    """

    yield from stopflow(
        exposure=0.1,
        post_stop_frames=10,
        pre_stop_frames=10,
        shutter_time=4e-3,
        panda=panda,
        detectors=detectors,
        baseline=baseline,
    )


def stress_test_stopflow(
    exposure: float = 1.0 / 250.0,
    post_stop_frames: int = 2000,
    pre_stop_frames: int = 8000,
    panda: HDFPanda = DEFAULT_PANDA,
    detectors: set[StandardDetector] = FAST_DETECTORS,
    baseline: set[Readable] = DEFAULT_BASELINE_MEASUREMENTS,
) -> MsgGenerator:
    yield from stopflow(
        exposure=exposure,
        post_stop_frames=post_stop_frames,
        pre_stop_frames=pre_stop_frames,
        shutter_time=4e-3,
        panda=panda,
        detectors=detectors,
        baseline=baseline,
    )


def save_device_for_stopflow(panda: HDFPanda = DEFAULT_PANDA) -> MsgGenerator:
    yield from save_device(panda, _PLAN_NAME)


# main
def stopflow(
    exposure: float,
    post_stop_frames: int,
    pre_stop_frames: int = 0,
    shutter_time: float = 4e-3,
    panda: HDFPanda = DEFAULT_PANDA,
    detectors: set[StandardDetector] = DEFAULT_DETECTORS,
    baseline: set[Readable] = DEFAULT_BASELINE_MEASUREMENTS,
    metadata: dict[str, Any] | None = None,
) -> MsgGenerator:
    """
    Perform a stop flow measurement, see detailed description in
    https://github.com/DiamondLightSource/i22-bluesky/issues/13

    Args:
        exposure: exposure time of the detectors (excluding deadtime).
        post_stop_frames: Number of frames to be collected after the flow
            is stopped.
        pre_stop_frames: Number of frames (if any) to be collected before
            the flow is stopped.
        shutter_time: Time period (seconds) to wait for the shutter to
            open fully before beginning acquisition.
        panda: PandA for controlling flyable motion.
        detectors: A set of detectors that will be collected.
        baseline: A set of devices to be read at the start and end of the plan
            in a stream names baseline.

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

    # Collect metadata
    plan_args = {
        "pre_stop_frames": pre_stop_frames,
        "post_stop_frames": post_stop_frames,
        "exposure": exposure,
        "shutter_time": shutter_time,
        "panda": panda.name + ":" + repr(panda),
        "detectors": {device.name + ":" + repr(device) for device in detectors},
        "baseline": {device.name + ":" + repr(device) for device in baseline},
    }
    # Add panda to detectors so it captures and writes data.
    # It needs to be in metadata but not metadata planargs.
    _md = {
        "detectors": {device.name for device in detectors},
        "plan_args": plan_args,
        "hints": {},
    }
    _md.update(metadata or {})
    detectors = detectors | {panda}

    @bpp.baseline_decorator(baseline)
    @attach_data_session_metadata_decorator()
    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_stopflow_plan():
        yield from load_device(panda, _PLAN_NAME)
        yield from prepare_seq_table_flyer_and_det(
            flyer=flyer,
            detectors=detectors,
            pre_stop_frames=pre_stop_frames,
            post_stop_frames=post_stop_frames,
            exposure=exposure,
            shutter_time=shutter_time,
        )
        yield from fly_and_collect(
            stream_name=stream_name,
            detectors=detectors,
            flyer=flyer,
        )

    yield from inner_stopflow_plan()
