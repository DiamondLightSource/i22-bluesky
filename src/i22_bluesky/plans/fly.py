from typing import List

from bluesky import preprocessors as bpp
from dodal.common import inject
from dodal.devices.focusing_mirror import FocusingMirror
from dodal.devices.i22.fswitch import FSwitch
from dodal.devices.slits import Slits
from ophyd_async.core import Device
from ophyd_async.core.detector import StandardDetector
from ophyd_async.core.flyer import HardwareTriggeredFlyable
from ophyd_async.panda._trigger import SeqTableInfo
from ophyd_async.plan_stubs.fly import (
    time_resolved_fly_and_collect_with_static_seq_table,
)


def alt_decorated_fly_2(
    stream_name: str,
    detectors: List[StandardDetector],
    flyer: HardwareTriggeredFlyable[SeqTableInfo],
    number_of_frames: int,
    exposure: int,
    shutter_time: float,
    repeats: int = 1,
    period: float = 0.0,
    baseline: List[Device] = [
        inject("fswitch"),
        inject("slits_1"),
        inject("slits_2"),
        inject("slits_3"),
        inject("slits_4"),
        inject("slits_5"),
        inject("slits_6"),
        inject("hfm"),
        inject("vfm"),
    ],
):
    @bpp.baseline_decorator(devices=baseline)
    def inner_fly():
        yield from time_resolved_fly_and_collect_with_static_seq_table(
            stream_name,
            detectors,
            flyer,
            number_of_frames,
            exposure,
            shutter_time,
            repeats,
            period,
        )

    yield from inner_fly()


def alt_decorated_fly_1(
    stream_name: str,
    detectors: List[StandardDetector],
    flyer: HardwareTriggeredFlyable[SeqTableInfo],
    number_of_frames: int,
    exposure: int,
    shutter_time: float,
    repeats: int = 1,
    period: float = 0.0,
    baseline: List[Device] = inject(
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
):
    @bpp.baseline_decorator(devices=baseline)
    def inner_fly():
        yield from time_resolved_fly_and_collect_with_static_seq_table(
            stream_name,
            detectors,
            flyer,
            number_of_frames,
            exposure,
            shutter_time,
            repeats,
            period,
        )

    yield from inner_fly()


def decorated_fly(
    stream_name: str,
    detectors: List[StandardDetector],
    flyer: HardwareTriggeredFlyable[SeqTableInfo],
    number_of_frames: int,
    exposure: int,
    shutter_time: float,
    repeats: int = 1,
    period: float = 0.0,
    fswitch: FSwitch = inject("fswitch"),
    slits_1: Slits = inject("slits_1"),
    slits_2: Slits = inject("slits_2"),
    slits_3: Slits = inject("slits_3"),
    slits_4: Slits = inject("slits_4"),
    slits_5: Slits = inject("slits_5"),
    slits_6: Slits = inject("slits_6"),
    hfm: FocusingMirror = inject("hfm"),
    vfm: FocusingMirror = inject("vfm"),
):
    @bpp.baseline_decorator(
        devices=[
            fswitch,
            slits_1,
            slits_2,
            slits_3,
            slits_4,
            slits_5,
            slits_6,
            hfm,
            vfm,
        ]
    )
    def inner_fly():
        yield from time_resolved_fly_and_collect_with_static_seq_table(
            stream_name,
            detectors,
            flyer,
            number_of_frames,
            exposure,
            shutter_time,
            repeats,
            period,
        )

    yield from inner_fly()
