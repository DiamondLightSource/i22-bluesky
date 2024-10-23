from __future__ import annotations

import bluesky.plan_stubs as bps
import numpy as np
from bluesky.utils import MsgGenerator
from dodal.common.coordination import group_uuid
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import StandardDetector, StandardFlyer
from ophyd_async.epics.adcore import (
    ADBaseIO,
    NDAttributePv,
    NDAttributePvDbrType,
)
from ophyd_async.fastcs.panda import HDFPanda
from ophyd_async.plan_stubs import (
    fly_and_collect,
    prepare_static_seq_table_flyer_and_detectors_with_same_trigger,
    setup_ndattributes,
)
from pydantic import BaseModel, Field, model_validator

from i22_bluesky.stubs.panda import load_panda_for_plan, save_panda_for_plan
from i22_bluesky.util.default_devices import PANDA

LINKAM_FOLDER = "linkam"


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
        assert (
            self.num is not None or self.step is not None
        ), "Must have set at least one of 'num', 'step'"
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


def stamp_temp_pv(linkam: Linkam3, stamped_detector: StandardDetector):
    assert isinstance(driver := stamped_detector.drv, ADBaseIO)
    yield from setup_ndattributes(
        driver,
        [
            NDAttributePv(
                "Temperature",
                linkam.temperature,
                dbrtype=NDAttributePvDbrType.DBR_FLOAT,
                description="Current linkam temperature",
            )
        ],
    )


def save_panda_config_for_stopflow(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from save_panda_for_plan(LINKAM_FOLDER, panda)


def load_panda_config_for_stopflow(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from load_panda_for_plan(LINKAM_FOLDER, panda)
