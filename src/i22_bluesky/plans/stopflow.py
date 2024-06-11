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

from typing import Any, Dict, List, Optional

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import bluesky.preprocessors as bpp
from bluesky.protocols import Readable
from dls_bluesky_core.core import MsgGenerator
from dodal.common import inject
from dodal.plans.data_session_metadata import attach_data_session_metadata_decorator
from ophyd_async.core import HardwareTriggeredFlyable
from ophyd_async.core.detector import DetectorTrigger, StandardDetector, TriggerInfo
from ophyd_async.core.utils import in_micros
from ophyd_async.panda import HDFPanda, StaticSeqTableTriggerLogic
from ophyd_async.panda._table import (
    SeqTable,
    SeqTableRow,
    SeqTrigger,
    seq_table_from_rows,
)
from ophyd_async.panda._trigger import SeqTableInfo
from ophyd_async.plan_stubs import fly_and_collect

DEFAULT_DETECTORS = [
    "saxs",
    "waxs",
    # "oav",
    "i0",
    "it",
]

DEFAULT_BASELINE_MEASUREMENTS = [
    "fswitch",
    "slits_1",
    "slits_2",
    "slits_3",
    # "slits_4", Until we make this device
    "slits_5",
    "slits_6",
    "hfm",
    "vfm",
]

DEFAULT_PANDA = "panda1"


@attach_data_session_metadata_decorator()
def count_stopflow_devices(
    num: int = 1,
    devices: list[Readable] = inject(
        DEFAULT_DETECTORS + DEFAULT_BASELINE_MEASUREMENTS + [DEFAULT_PANDA]
    ),
) -> MsgGenerator:
    """
    Take a reading from all devices that are used in the
    stopflow plan by default
    """

    yield from bp.count(devices, num=num)


def stopflow(
    exposure: float,
    post_stop_frames: int,
    pre_stop_frames: int = 0,
    shutter_time: float = 4e-3,
    panda: HDFPanda = inject(DEFAULT_PANDA),
    detectors: List[StandardDetector] = inject(DEFAULT_DETECTORS),
    baseline: List[Readable] = inject(DEFAULT_BASELINE_MEASUREMENTS),
    metadata: Optional[Dict[str, Any]] = None,
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
        detectors: A list of detectors that will be collected.
        baseline: A list of devices to be read at the start and end of the plan
            in a stream names baseline.

    Returns:
        MsgGenerator: Plan

    Yields:
        Iterator[MsgGenerator]: Bluesky messages
    """
    stream_name = "main"
    flyer = HardwareTriggeredFlyable(StaticSeqTableTriggerLogic(panda.seq[1]))
    devices = [flyer] + detectors + [panda] + baseline

    # Collect metadata
    plan_args = {
        "pre_stop_frames": pre_stop_frames,
        "post_stop_frames": post_stop_frames,
        "exposure": exposure,
        "shutter_time": shutter_time,
        "panda": repr(panda),
        "detectors": [repr(device) for device in detectors],
        "baseline": [repr(device) for device in baseline],
    }
    # Add panda to detectors so it captures and writes data.
    # It needs to be in metadata but not metadata planargs.
    _md = {
        "detectors": [device.name for device in detectors],
        "plan_args": plan_args,
        "hints": {},
    }
    _md.update(metadata or {})
    detectors = detectors + [panda]

    @bpp.baseline_decorator(baseline)
    @attach_data_session_metadata_decorator()
    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_stopflow_plan():
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


def prepare_seq_table_flyer_and_det(
    flyer: HardwareTriggeredFlyable[SeqTableInfo],
    detectors: List[StandardDetector],
    pre_stop_frames: int,
    post_stop_frames: int,
    exposure: float,
    shutter_time: float,
    period: float = 0.0,
) -> MsgGenerator:
    """
    Setup detectors/flyer for a stop flow experiment. Create a seq table and
    upload it to the panda. Arm all detectors.

    Args:
        flyer: Flyer object that controls the panda
        detectors: Detectors that are triggered by the panda
        post_stop_frames: Number of frames to be collected after the flow
            is stopped.
        pre_stop_frames: Number of frames (if any) to be collected before
            the flow is stopped.
        exposure: Detector exposure time
        shutter_time: Time period (seconds) to wait for the shutter to
            open fully before beginning acquisition
        period: Time period (seconds) to wait after arming the detector
            before taking the first batch of frames

    Returns:
        MsgGenerator: Plan

    Yields:
        Iterator[MsgGenerator]: Bluesky messages
    """

    deadtime = max(det.controller.get_deadtime(exposure) for det in detectors)
    trigger_info = TriggerInfo(
        num=(pre_stop_frames + post_stop_frames),
        trigger=DetectorTrigger.constant_gate,
        deadtime=deadtime,
        livetime=exposure,
    )

    # Generate a seq table
    table = stopflow_seq_table(
        pre_stop_frames,
        post_stop_frames,
        exposure,
        shutter_time,
        deadtime,
        period,
    )
    table_info = SeqTableInfo(table, repeats=1)

    # Upload the seq table and arm all detectors.
    for det in detectors:
        yield from bps.prepare(det, trigger_info, wait=False, group="prep")
    yield from bps.prepare(flyer, table_info, wait=False, group="prep")
    yield from bps.wait(group="prep")


def stopflow_seq_table(
    pre_stop_frames: int,
    post_stop_frames: int,
    exposure: float,
    shutter_time: float,
    deadtime: float,
    period: float,
) -> SeqTable:
    """Create a SeqTable based on the parameters of a stop flow measurement

    Args:
        pre_stop_frames: Number of frames to take initially, before flow stops
        post_stop_frames: Number of frames to take after flow stops
        exposure: Exposure time of each frame (excluding deadtime)
        shutter_time: Time period (seconds) to wait for the shutter to open fully before
            beginning acquisition
        deadtime: Dead time to leave between frames, dependant on the
            instruments involved
        period: Time period (seconds) to wait after arming the detector
            before taking the first batch of frames

    Returns:
        SeqTable: SeqTable that will result in a series of triggers for the measurement
    """

    total_gate_time = (pre_stop_frames + post_stop_frames) * (exposure + deadtime)
    pre_delay = max(period - 2 * shutter_time - total_gate_time, 0)

    return seq_table_from_rows(
        # Wait for pre-delay then open shutter
        SeqTableRow(
            time1=in_micros(pre_delay),
            time2=in_micros(shutter_time),
            outa2=True,
        ),
        # Keeping shutter open, do n triggers
        SeqTableRow(
            repeats=pre_stop_frames,
            time1=in_micros(exposure),
            outa1=True,
            outb1=True,
            time2=in_micros(deadtime),
            outa2=True,
        ),
        # Do m triggers after BITA=1
        SeqTableRow(
            trigger=SeqTrigger.BITA_1,
            repeats=post_stop_frames,
            time1=in_micros(exposure),
            outa1=True,
            outb1=True,
            time2=in_micros(deadtime),
            outa2=True,
        ),
        # Add the shutter close
        SeqTableRow(time2=in_micros(shutter_time)),
    )
