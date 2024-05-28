# Stop flow experiment

# The experiment involves a liquid sample intersecting and flowing laterally to the beam.
# The beam passes through the flowing liquid and scatters onto a detector.
# The flow is controlled by a proprietary rig that allows the user to request a "stop flow".
# At the moment the flow stops, the rig sends out a pulse to the panda, which can then trigger the detector.

# A single pulse goes into the panda and many pulses come out via a sequencer table.
# The table can specify X sets of Y pulses at Z hertz.

# Frames may also be collected before waiting for the trigger.

# As such the implementation is:
# start acquisition -> acquire n frames -> wait for trigger -> acquire m frames
# where n can be 0.

from typing import List

import bluesky.plan_stubs as bps
from bluesky.protocols import Readable
import bluesky.preprocessors as bpp

from dodal.common import MsgGenerator, inject
from dodal.common.visit import attach_metadata_decorator

from ophyd_async.core import HardwareTriggeredFlyable
from ophyd_async.core.detector import DetectorTrigger, StandardDetector, TriggerInfo
from ophyd_async.core.utils import in_micros
from ophyd_async.panda import HDFPanda, StaticSeqTableTriggerLogic
from ophyd_async.plan_stubs import time_resolved_fly_and_collect_with_static_seq_table
from ophyd_async.panda._table import (
    SeqTable,
    SeqTableRow,
    seq_table_from_rows,
    SeqTrigger,
)
from ophyd_async.panda._trigger import SeqTableInfo


def stopflow(
    pre_stop_frames: int,
    post_stop_frames: int,
    exposure: int,
    shutter_time: float,
    panda: HDFPanda,
    detectors: List[StandardDetector],
    baseline: List[Readable] = inject(
        [
            "fswitch",
            "slits_1",
            "slits_2",
            "slits_3",
            "slits_4",
            "slits_5",
            "slits_6",
            "hfm",
            "vfm",
        ]
    ),
) -> MsgGenerator:
    """
    Args:
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
    devices = [flyer] + detectors + baseline

    # Trigger information
    number_of_frames = pre_stop_frames + post_stop_frames
    repeats: int = 1
    period: float = 0

    @bpp.baseline_decorator(baseline)
    @attach_metadata_decorator(provider=None)
    @bpp.stage_decorator(devices)
    @bpp.run_decorator()
    def inner_stopflow_plan():
        yield from time_resolved_fly_and_collect_with_static_seq_table(
            stream_name=stream_name,
            detectors=detectors,
            flyer=flyer,
            number_of_frames=number_of_frames,
            exposure=exposure,
            shutter_time=shutter_time,
            repeats=repeats,
            period=period,
            prepare_flyer_and_detectors=prepare_seq_table_flyer_and_det,
        )
    yield from inner_stopflow_plan()

def prepare_seq_table_flyer_and_det(
    flyer: HardwareTriggeredFlyable[SeqTableInfo],
    detectors: List[StandardDetector],
    pre_stop_frames: int,
    post_stop_frames: int,
    exposure: float,
    deadtime: float,
    shutter_time: float,
    period: float = 0.0,
):

    trigger_info = TriggerInfo(
        num=(pre_stop_frames + post_stop_frames),
        trigger=DetectorTrigger.constant_gate,
        deadtime=deadtime,
        livetime=exposure,
    )

    trigger_time = (pre_stop_frames + post_stop_frames) * (exposure + deadtime)
    pre_delay = max(period - 2 * shutter_time - trigger_time, 0)

    table: SeqTable = seq_table_from_rows(
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

    table_info = SeqTableInfo(table, repeats=1)

    for det in detectors:
        yield from bps.prepare(det, trigger_info, wait=False, group="prep")
    yield from bps.prepare(flyer, table_info, wait=False, group="prep")
    yield from bps.wait(group="prep")
