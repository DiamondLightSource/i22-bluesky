import bluesky.plan_stubs as bps
from bluesky.utils import MsgGenerator
from ophyd_async.core import (
    DetectorTrigger,
    StandardDetector,
    StandardFlyer,
    TriggerInfo,
    in_micros,
)
from ophyd_async.fastcs.panda._table import (
    SeqTable,
    SeqTrigger,
)
from ophyd_async.fastcs.panda._trigger import SeqTableInfo

from i22_bluesky.util.baseline import DEADTIME_BUFFER


def prepare_seq_table_flyer_and_det(
    flyer: StandardFlyer[SeqTableInfo],
    detectors: set[StandardDetector],
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

    deadtime = (
        max(det.controller.get_deadtime(exposure) for det in detectors)
        + DEADTIME_BUFFER
    )
    trigger_info = TriggerInfo(
        num=(pre_stop_frames + post_stop_frames),
        trigger=DetectorTrigger.constant_gate,
        deadtime=deadtime,
        livetime=exposure,
        frame_timeout=60.0,
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
            shutter_time: Time period (seconds) to wait for the shutter
                    to open fully before beginning acquisition
            deadtime: Dead time to leave between frames, dependant on the
                    instruments involved
            period: Time period (seconds) to wait after arming the detector
                    before taking the first batch of frames

    Returns:
            SeqTable: SeqTable that will result in a series of triggers
                    for the measurement
    """

    total_gate_time = (pre_stop_frames + post_stop_frames) * (exposure + deadtime)
    pre_delay = max(period - 2 * shutter_time - total_gate_time, 0)
    # Wait for pre-delay then open shutter
    table = SeqTable.row(
        time1=in_micros(pre_delay),
        time2=in_micros(shutter_time),
        outa2=True,
    )

    # Keeping shutter open, do n triggers
    if pre_stop_frames > 0:
        table += SeqTable.row(
            repeats=pre_stop_frames,
            time1=in_micros(exposure),
            outa1=True,
            outb1=True,
            time2=in_micros(deadtime),
            outa2=True,
        )
    # Do m triggers after BITA=1
    if post_stop_frames > 0:
        table += SeqTable.row(
            trigger=SeqTrigger.BITA_1,
            repeats=1,
            time1=in_micros(exposure),
            outa1=True,
            outb1=True,
            time2=in_micros(deadtime),
            outa2=True,
        )
        if post_stop_frames > 1:
            table += SeqTable.row(
                repeats=post_stop_frames - 1,
                time1=in_micros(exposure),
                outa1=True,
                outb1=True,
                time2=in_micros(deadtime),
                outa2=True,
            )
    # Add the shutter close
    table += SeqTable.row(time2=in_micros(shutter_time))
    return table


def raise_for_minimum_exposure_times(
    exposure: float,
    detectors: set[StandardDetector],
) -> None:
    minimum_exposure_times = {
        "saxs": 1.0 / 250.0,
        "waxs": 1.0 / 250.0,
        "oav": 1.0 / 22.0,
        "i0": 1.0 / 2e4,
        "it": 1.0 / 2e4,
    }
    detectors_below_limit = {
        detector
        for detector in detectors
        if exposure < minimum_exposure_times.get(detector.name, 0.0)
    }
    if len(detectors_below_limit) > 0:
        raise KeyError(
            f"The exposure time requested was {exposure}, but "
            "the following detectors do not support going "
            f"that fast: {detectors_below_limit}. Try running the plan"
            "without them. "
            f"See minimum exposure time table: {minimum_exposure_times}"
        )
