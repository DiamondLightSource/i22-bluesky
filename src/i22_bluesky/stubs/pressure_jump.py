from typing import cast

import bluesky.plan_stubs as bps
from bluesky.utils import MsgGenerator
from ophyd_async.core import (
    DetectorController,
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
    pre_jump_frames: int,
    post_jump_frames: int,
    exposure: float,
    shutter_time: float,
    period: float = 0.0,
) -> MsgGenerator:
    """
    Setup detectors/flyer for a pressure jump experiment. Create a seq table and
    upload it to the panda. Arm all detectors.

    Args:
            flyer: Flyer object that controls the panda
            detectors: Detectors that are triggered by the panda
            post_jump_frames: Number of frames to be collected after the pressure jumps.
            pre_jump_frames: Number of frames (if any) to be collected before
                    the pressure jumps.
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
        max(
            cast(DetectorController, det._controller).get_deadtime(exposure)  # noqa: SLF001
            for det in detectors
        )
        + DEADTIME_BUFFER
    )
    trigger_info = TriggerInfo(
        number_of_events=(pre_jump_frames + post_jump_frames),
        trigger=DetectorTrigger.CONSTANT_GATE,
        deadtime=deadtime,
        livetime=exposure,
        exposure_timeout=60.0,
    )

    # Generate a seq table
    table = pressure_jump_seq_table(
        pre_jump_frames,
        post_jump_frames,
        exposure,
        shutter_time,
        deadtime,
        period,
    )
    table_info = SeqTableInfo(sequence_table=table, repeats=1)

    # Upload the seq table and arm all detectors.
    for det in detectors:
        yield from bps.prepare(det, trigger_info, wait=False, group="prep")
    yield from bps.prepare(flyer, table_info, wait=False, group="prep")
    yield from bps.wait(group="prep")


def pressure_jump_seq_table(
    pre_jump_frames: int,
    post_jump_frames: int,
    exposure: float,
    shutter_time: float,
    deadtime: float,
    period: float,
) -> SeqTable:
    """Create a SeqTable based on the parameters of a a pressure jump measurement

    Args:
            pre_jump_frames: Number of frames to take initially, after pressure jumps
            post_jump_frames: Number of frames to take after pressure jumps
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

    total_gate_time = (pre_jump_frames + post_jump_frames) * (exposure + deadtime)
    pre_delay = max(period - 2 * shutter_time - total_gate_time, 0)

    # Wait for pre-delay then open shutter
    table = SeqTable.row(
        time1=in_micros(pre_delay), time2=in_micros(shutter_time), outa2=True
    )

    # Keeping shutter open, do n triggers
    if pre_jump_frames > 0:
        table += SeqTable.row(
            repeats=pre_jump_frames,
            time1=in_micros(exposure),
            outa1=True,
            outb1=True,
            time2=in_micros(deadtime),
            outa2=True,
        )
    # todo not sure how do we get the trigger exactly
    # Do m triggers after BITA=1
    if post_jump_frames > 0:
        table += SeqTable.row(
            trigger=SeqTrigger.BITA_1,
            repeats=1,
            time1=in_micros(exposure),
            outa1=True,
            outb1=True,
            time2=in_micros(deadtime),
            outa2=True,
        )
        if post_jump_frames > 1:
            table += SeqTable.row(
                repeats=post_jump_frames - 1,
                time1=in_micros(exposure),
                outa1=True,
                outb1=True,
                time2=in_micros(deadtime),
                outa2=True,
            )
    # Add the shutter close
    table += SeqTable.row(time2=in_micros(shutter_time))
    return table
