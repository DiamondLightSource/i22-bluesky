from typing import List

import bluesky.preprocessors as bpp
from dls_bluesky_core.core.types import MsgGenerator
from dodal.common import inject
from dodal.common.visit import attach_metadata_decorator
from ophyd_async.core import Device, HardwareTriggeredFlyable, StandardDetector
from ophyd_async.panda import HDFPanda
from ophyd_async.panda._trigger import StaticSeqTableTriggerLogic
from ophyd_async.plan_stubs.fly import (
    time_resolved_fly_and_collect_with_static_seq_table,
)


def decorated_fly(
    stream_name: str,
    detectors: List[StandardDetector],
    panda: HDFPanda,
    number_of_frames: int,
    exposure: int,
    shutter_time: float,
    repeats: int = 1,
    period: float = 0.0,
    baseline: List[Device] = inject(  # TODO: Readable?
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
    devices = [panda] + detectors + baseline

    @bpp.baseline_decorator(baseline)
    @attach_metadata_decorator(provider=None)
    @bpp.stage_decorator(devices)
    @bpp.run_decorator()
    def inner_fly():
        yield from time_resolved_fly_and_collect_with_static_seq_table(
            stream_name,
            detectors,
            HardwareTriggeredFlyable(StaticSeqTableTriggerLogic(panda.seq[1])),
            number_of_frames,
            exposure,
            shutter_time,
            repeats,
            period,
        )

    yield from inner_fly()
