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

import bluesky.plan_stubs as bps
from dodal.common import MsgGenerator
from ophyd_async.core import HardwareTriggeredFlyable
from ophyd_async.core.detector import StandardDetector
from ophyd_async.panda import HDFPanda, StaticSeqTableTriggerLogic
from ophyd_async.plan_stubs import time_resolved_fly_and_collect_with_static_seq_table


def stopflow(
    panda: HDFPanda,
    det1: StandardDetector


) -> MsgGenerator:
    """
    Args:
        panda: PandA for controlling flyable motion

    Returns:
        MsgGenerator: Plan

    Yields:
        Iterator[MsgGenerator]: Bluesky messages
    """

    stream_name = "main"
    detectors = [det1]
    flyer = HardwareTriggeredFlyable(StaticSeqTableTriggerLogic(panda.seq[1]))

    # Trigger information
    number_of_frames: int
    exposure: int
    shutter_time: float
    repeats: int = 1
    period: float = 0


    yield from bps.stage_all(*detectors, flyer)
    yield from bps.open_run()

    time_resolved_fly_and_collect_with_static_seq_table(
        stream_name=stream_name,
        detectors = detectors,
        flyer=flyer,
        number_of_frames=number_of_frames,
        exposure=exposure,
        shutter_time=shutter_time,
        repeats=repeats,
        period=period,
    )

    yield from bps.close_run()
    yield from bps.unstage_all(flyer, *detectors)
