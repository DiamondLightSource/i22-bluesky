from __future__ import annotations

import bluesky.plan_stubs as bps
import numpy as np
from dodal.common import MsgGenerator
from dodal.common.coordination import group_uuid
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import (
    DetectorTrigger,
    StandardDetector,
    StandardFlyer,
    TriggerInfo,
    in_micros,
)
from ophyd_async.fastcs.panda import (
    SeqTable,
    SeqTableInfo,
)
from pydantic import BaseModel, Field, model_validator

from i22_bluesky.stubs.fly_and_collect import fly_and_collect


def prepare_static_seq_table_flyer_and_detectors_with_same_trigger(
    flyer: StandardFlyer[SeqTableInfo],
    detectors: list[StandardDetector],
    number_of_frames: int,
    exposure: float,
    shutter_time: float,
    repeats: int = 1,
    period: float = 0.0,
    frame_timeout: float | None = None,
):
    """Prepare a hardware triggered flyable and one or more detectors.

    Prepare a hardware triggered flyable and one or more detectors with the
    same trigger. This method constructs TriggerInfo and a static sequence
    table from required parameters. The table is required to prepare the flyer,
    and the TriggerInfo is required to prepare the detector(s).

    This prepares all supplied detectors with the same trigger.

    """
    if not detectors:
        raise ValueError("No detectors provided. There must be at least one.")

    deadtime = max(det._controller.get_deadtime(exposure) for det in detectors)  # noqa: SLF001

    trigger_info = TriggerInfo(
        number_of_events=number_of_frames * repeats,
        trigger=DetectorTrigger.CONSTANT_GATE,
        deadtime=deadtime,
        livetime=exposure,
        exposure_timeout=frame_timeout,
    )
    trigger_time = number_of_frames * (exposure + deadtime)
    pre_delay = max(period - 2 * shutter_time - trigger_time, 0)

    table = (
        # Wait for pre-delay then open shutter
        SeqTable.row(
            time1=in_micros(pre_delay),
            time2=in_micros(shutter_time),
            outa2=True,
        )
        +
        # Keeping shutter open, do N triggers
        SeqTable.row(
            repeats=number_of_frames,
            time1=in_micros(exposure),
            outa1=True,
            outb1=True,
            time2=in_micros(deadtime),
            outa2=True,
        )
        +
        # Add the shutter close
        SeqTable.row(time2=in_micros(shutter_time))
    )

    table_info = SeqTableInfo(sequence_table=table, repeats=repeats)

    for det in detectors:
        yield from bps.prepare(det, trigger_info, wait=False, group="prep")
    yield from bps.prepare(flyer, table_info, wait=False, group="prep")
    yield from bps.wait(group="prep")


class LinkamPathSegment(BaseModel):
    stop: float = Field(
        description="Target final temperature and initial temperature of next segment.",
        json_schema_extra={"units": "°C"},
    )
    rate: float = Field(
        description="Absolute value of temperature change rate |dT/dt|.",
        json_schema_extra={"units": "°C/minute"},
        gt=0.0,
    )
    step: float | None = Field(
        description="Temp change to generate points on this segment from. \
            Ignored if `num` if set. May be |dT| if stop < start.",
        json_schema_extra={"units": "°C"},
        default=None,
    )
    num: int | None = Field(
        description="Number of equally spaced points to capture along this segment. \
            Overrides `step` if set. 1 gives only start of segment.",
        gt=0,
        default=None,
    )
    num_frames: int | None = Field(
        description="Number of frames to capture at each captured point. \
            If not set, must be set for overall trajectory.",
        gt=0,
        default=None,
    )
    exposure: float | None = Field(
        description="Exposure time for detector(s) per frame. \
            If not set, must be set for overall trajectory.",
        gt=0.0,
        default=None,
        json_schema_extra={"units": "s"},
    )
    flown: bool = Field(
        description="Whether this segment should be flown (temperature controller \
            begins move, then frames are captured periodically) or stepped \
            (temperature controller moves, stops then frames are captured).",
        default=True,
    )

    @model_validator(mode="after")
    def check_num_or_step_set(self) -> LinkamPathSegment:
        assert self.num is not None or self.step is not None, (
            "Must have set at least one of 'num', 'step'"
        )
        return self


class LinkamTrajectory(BaseModel):
    start: float = Field(
        description="Initial temperature of 1st segment.",
        json_schema_extra={"units": "°C"},
    )
    path: list[LinkamPathSegment] = Field(
        description="Ordered list of segments describing the temperature path.",
        min_length=1,
    )
    default_num_frames: int | None = Field(
        description="Number of frames to collect if not overriden by segment. \
        Must be set if any segment does not define for itself.",
        gt=0,
        default=None,
    )
    default_exposure: float | None = Field(
        description="Exposure time for each frame if not overriden by segment. \
        Must be set if any segment does not define for itself.",
        gt=0.0,
        default=None,
        json_schema_extra={"units": "s"},
    )

    @model_validator(mode="after")
    def check_defaults(self) -> LinkamTrajectory:
        assert self.default_num_frames is not None or all(
            segment.num_frames is not None for segment in self.path
        ), "Number of frames not set for default and for some segment(s)!"
        assert self.default_exposure is not None or all(
            segment.exposure is not None for segment in self.path
        ), "Exposure not set for default and for some segment(s)!"
        return self


def capture_temp(
    linkam: Linkam3,
    flyer: StandardFlyer,
    detectors: list[StandardDetector],
    temp: float,
    num_frames: int,
    exposure: float,
    shutter_time: float = 0.04,
    stream_name: str = "primary",
):
    yield from bps.mv(linkam, temp)
    yield from prepare_static_seq_table_flyer_and_detectors_with_same_trigger(
        flyer=flyer,
        detectors=detectors,
        number_of_frames=num_frames,
        exposure=exposure,
        shutter_time=shutter_time,
    )
    yield from fly_and_collect(
        stream_name=stream_name,
        flyer=flyer,
        detectors=detectors,
    )


def capture_linkam_segment(
    linkam: Linkam3,
    flyer: StandardFlyer,
    detectors: set[StandardDetector],
    start: float,
    stop: float,
    num: int,
    rate: float,
    num_frames: int,
    exposure: float,
    shutter_time: float = 0.04,
    stream_name: str = "primary",
    fly: bool = False,
) -> MsgGenerator:
    # Move to start in case previous segment has misaligned step
    yield from bps.mv(linkam, start)
    # Set temperature ramp rate to expected for segment
    yield from bps.mv(linkam.ramp_rate, rate)

    ordered_detectors = list(detectors)
    if not fly:
        # Move, stop then collect at each step
        for temp in np.linspace(start, stop, num):
            yield from capture_temp(
                linkam,
                flyer,
                ordered_detectors,
                temp,
                num_frames,
                exposure,
                shutter_time,
                stream_name,
            )
    else:
        # Kick off move, capturing periodically
        yield from prepare_static_seq_table_flyer_and_detectors_with_same_trigger(
            flyer=flyer,
            detectors=ordered_detectors,
            number_of_frames=num * num_frames,
            exposure=exposure,
            shutter_time=shutter_time,
            period=abs(stop - start / (rate / 60)),  # period in s, dT/(dT/dt)
        )
        linkam_group = group_uuid("linkam")
        yield from bps.abs_set(linkam, stop, group=linkam_group, wait=False)
        yield from fly_and_collect(
            stream_name=stream_name,
            flyer=flyer,
            detectors=ordered_detectors,
        )
        # Make sure linkam has finished
        yield from bps.wait(group=linkam_group)
