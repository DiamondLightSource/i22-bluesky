from __future__ import annotations

from typing import Annotated, Any

import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
import numpy as np
from bluesky.utils import MsgGenerator
from dodal.common.coordination import group_uuid
from dodal.common.maths import step_to_num
from dodal.devices.linkam3 import Linkam3
from dodal.plans.data_session_metadata import attach_data_session_metadata_decorator
from ophyd_async.core import StandardDetector, StandardFlyer
from ophyd_async.epics.adcore import (
    ADBaseIO,
    NDAttributePv,
    NDAttributePvDbrType,
)
from ophyd_async.fastcs.panda import HDFPanda, StaticSeqTableTriggerLogic
from ophyd_async.plan_stubs import (
    fly_and_collect,
    prepare_static_seq_table_flyer_and_detectors_with_same_trigger,
    setup_ndattributes,
    setup_ndstats_sum,
)
from pydantic import BaseModel, Field, model_validator, validate_call

from i22_bluesky.stubs.panda import load_panda_config_for_linkam
from i22_bluesky.util.default_devices import (
    DETECTORS,
    LINKAM,
    PANDA,
    STAMPED_DETECTOR,
)


@attach_data_session_metadata_decorator()
@validate_call(config={"arbitrary_types_allowed": True})
def linkam_plan(
    trajectory: Annotated[LinkamTrajectory, "Trajectory for the scan to follow."],
    linkam: Annotated[Linkam3, "Temperature controller."] = LINKAM,
    panda: Annotated[
        HDFPanda,
        "Panda with sequence table configured and connected to \
        FastShutter (outa) and each of detectors (outb).",
    ] = PANDA,
    stamped_detector: Annotated[
        StandardDetector,
        "AreaDetector to configure to stamp the Linkam temperature. \
            Will be automatically added to detectors if not included.",
    ] = STAMPED_DETECTOR,
    detectors: Annotated[
        set[StandardDetector], "Detectors to capture at each temperature value"
    ] = DETECTORS,
    shutter_time: Annotated[
        float, "Time allowed for opening shutter before triggering detectors."
    ] = 0.04,
    stream_name: Annotated[str, "Stream name for bluesky documents."] = "primary",
    metadata: dict[str, Any] | None = None,
) -> MsgGenerator:
    """
    Follow a trajectory in temperature, collecting a number of frames either at equally
    spaced positions or while continually scanning. e.g. for 2 segments, the first
    stepped and the 2nd flown:\n
    trajectory start   v             v final segment stop\n
                       \\           /\n
       stepped segment__\\__       /\n
                           \\     /  flown segment\n
           1st segment stop \\__ /\n
        exposures:    xx  xx  xx   1/N seconds
    """
    flyer = StandardFlyer(StaticSeqTableTriggerLogic(panda.seq[1]))
    detectors = detectors | {stamped_detector}
    devices = detectors | {linkam, panda}

    plan_args = {
        "trajectory": trajectory,
        "linkam": linkam.name,
        "panda": panda.name,
        "stamped_detector": stamped_detector.name,
        "detectors": {detector.name for detector in detectors},
    }
    _md = {
        "detectors": {device.name for device in detectors},
        "motors": {linkam.name},
        "plan_args": plan_args,
        # TODO: Can we pass dimensional hint? motors? shape?
        "hints": {},
    }
    _md.update(metadata or {})

    yield from load_panda_config_for_linkam(panda)
    yield from _stamp_temp_pv(linkam, stamped_detector)
    for det in detectors:
        yield from setup_ndstats_sum(det)

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_linkam_plan():
        start = trajectory.start
        for segment in trajectory.path:
            start, stop, num = (
                start,
                segment.stop,
                segment.num
                if segment.num is not None
                else step_to_num(start, segment.stop, segment.step),
            )
            yield from _capture_linkam_segment(
                linkam,
                flyer,
                detectors,
                start,
                stop,
                num,
                segment.rate,
                segment.num_frames or trajectory.default_num_frames,
                segment.exposure or trajectory.default_exposure,
                fly=segment.flown,
                shutter_time=shutter_time,
                stream_name=stream_name,
            )
            start = segment.stop

    rs_uid = yield from inner_linkam_plan()
    return rs_uid


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


def _capture_temp(
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


def _capture_linkam_segment(
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
            yield from _capture_temp(
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


def _stamp_temp_pv(linkam: Linkam3, stamped_detector: StandardDetector):
    assert isinstance(driver := stamped_detector.drv, ADBaseIO)
    yield from setup_ndattributes(
        driver,
        [
            NDAttributePv(
                "Temperature",
                linkam.temp,
                dbrtype=NDAttributePvDbrType.DBR_FLOAT,
                description="Current linkam temperature",
            )
        ],
    )
