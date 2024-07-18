from typing import Self

import bluesky.plan_stubs as bps
import numpy as np
from dodal.common import MsgGenerator
from dodal.common.coordination import group_uuid
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import StandardDetector
from ophyd_async.core.flyer import HardwareTriggeredFlyable
from ophyd_async.plan_stubs import (
    fly_and_collect,
    prepare_static_seq_table_flyer_and_detectors_with_same_trigger,
)
from pydantic import BaseModel, Field, model_validator


class LinkamPathSegment(BaseModel):
    stop: float = Field(
        "Target final temperature, and initial temperature of next segment.",
        json_schema_extra={"units": "°C"},
    )
    rate: float = Field(
        "Absolute value of temperature change rate |dT/dt|.",
        json_schema_extra={"units": "°C/minute"},
        gt=0.0,
    )
    step: float | None = Field(
        "Temp change to generate points on this segment from. \
            Ignored if `num` if set. May be |dT| if stop < start.",
        json_schema_extra={"units": "°C"},
        default=None,
    )
    num: int | None = Field(
        "Number of equally spaced points to capture along this segment. \
            Overrides `step` if set. 1 gives only start of segment.",
        gt=0,
        default=None,
    )
    num_frames: int | None = Field(
        "Number of frames to capture at each captured point. \
            If not set, must be set for overall trajectory.",
        gt=0,
        default=None,
    )
    exposure: float | None = Field(
        "Exposure time for detector(s) per frame. \
            If not set, must be set for overall trajectory.",
        gt=0.0,
        default=None,
        json_schema_extra={"units": "s"},
    )
    flown: bool = Field(
        "Whether this segment should be flown (temperature controller begins move, \
        then frames are captured periodically) or stepped (temperature controller \
        moves, stops then frames are captured).",
        default=True,
    )

    @model_validator(mode="after")
    def check_num_or_step_set(self) -> Self:
        if self.num is None and self.step is None:
            raise ValueError("Must have set at least one of 'num', 'step'")
        return self


class LinkamTrajectory(BaseModel):
    start: float = Field(
        "Initial temperature of 1st segment.", json_schema_extra={"units": "°C"}
    )
    path: list[LinkamPathSegment] = Field(
        description="Ordered list of segments describing the temperature path.",
        min_length=1,
    )
    default_num_frames: int | None = Field(
        "Number of frames to collect if not overriden by segment. \
        Must be set if any segment does not define for itself.",
        gt=0,
        default=None,
    )
    default_exposure: float | None = Field(
        "Exposure time for each frame if not overriden by segment. \
        Must be set if any segment does not define for itself.",
        gt=0.0,
        default=None,
        json_schema_extra={"units": "s"},
    )

    @model_validator(mode="after")
    def check_defaults(self) -> Self:
        if self.default_num_frames is None and any(
            segment.num_frames is None for segment in self.path
        ):
            raise ValueError(
                "Number of frames not set for default and for some segment(s)!"
            )
        if self.default_exposure is None and any(
            segment.exposure is None for segment in self.path
        ):
            raise ValueError("Exposure not set for default and for some segment(s)!")
        return self


def capture_temp(
    linkam: Linkam3,
    flyer: HardwareTriggeredFlyable,
    detectors: set[StandardDetector],
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
    flyer: HardwareTriggeredFlyable,
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
    yield from bps.mv(start)
    # Set temperature ramp rate to expected for segment
    yield from bps.mv(linkam.ramp_rate, rate)

    if not fly:
        # Move, stop then collect at each step
        for temp in np.linspace(start, stop, num):
            yield from capture_temp(
                linkam,
                flyer,
                detectors,
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
            detectors=detectors,
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
            detectors=detectors,
        )
        # Make sure linkam has finished
        yield from bps.wait(group=linkam_group)
