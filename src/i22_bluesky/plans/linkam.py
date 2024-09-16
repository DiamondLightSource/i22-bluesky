from typing import Any

import bluesky.preprocessors as bpp
from dodal.common import MsgGenerator, inject
from dodal.common.maths import step_to_num
from dodal.devices.linkam3 import Linkam3
from dodal.plans.data_session_metadata import attach_data_session_metadata_decorator
from ophyd_async.core import HardwareTriggeredFlyable, StandardDetector
from ophyd_async.core.device_save_loader import load_device, save_device
from ophyd_async.panda import HDFPanda, StaticSeqTableTriggerLogic
from pydantic import Field

from i22_bluesky.stubs.linkam import (
    LinkamTrajectory,
    capture_linkam_segment,
)
from i22_bluesky.util.baseline import (
    DEFAULT_DETECTORS,
    DEFAULT_LINKAM,
    DEFAULT_PANDA,
)
from i22_bluesky.util.settings import (
    enable_stats_sum,
    get_ad_xml_dir,
    get_device_save_dir,
    stamp_temp_pv,
)

DEFAULT_STAMPED_DETECTOR: StandardDetector = inject("saxs")


def save_linkam(panda: HDFPanda = inject(DEFAULT_PANDA)) -> MsgGenerator:
    yield from save_device(
        panda,
        get_device_save_dir(linkam_plan.__name__),
        ignore=["pcap.capture", "data.capture", "data.datasets"],
    )


@attach_data_session_metadata_decorator()
def linkam_plan(
    trajectory: LinkamTrajectory = Field("Trajectory for the scan to follow."),
    linkam: Linkam3 = Field("Temperature controller.", default=DEFAULT_LINKAM),
    panda: HDFPanda = Field(
        "Panda with sequence table configured and connected to \
        FastShutter (outa) and each of detectors (outb).",
        default=DEFAULT_PANDA,
    ),
    stamped_detector: StandardDetector = Field(
        "AreaDetector to configure to stamp the Linkam temperature. \
            Will be automatically added to detectors if not included.",
        default=DEFAULT_STAMPED_DETECTOR,
    ),
    detectors: set[StandardDetector] = Field(
        "Detectors to capture at each temperature value", default=DEFAULT_DETECTORS
    ),
    shutter_time: float = Field(
        description="Time allowed for opening shutter before triggering detectors.",
        default=0.04,
        json_schema_extra={"units": "s"},
    ),
    stream_name: str = Field(
        description="Stream name for bluesky documents.", default="primary"
    ),
    metadata: dict[str, Any] | None = None,
) -> MsgGenerator:
    """
    Args:
        start_temp: Initial temperature to reach before starting experiment
        trajectory: Trajectory to follow: each segment begins at the end of the previous
        num_frames: Default number of frames at each captured point
        exposure: Default exposure for each frame
        linkam: Linkam temperature stage
        panda: PandA for controlling flyable motion
        stamped_detector: Detector to stamp temperature PV to H5 file
        detectors: Other StandardDetectors to capture

    Returns:
        MsgGenerator: Plan

    Yields:
        Iterator[MsgGenerator]: Bluesky messages
    """
    flyer = HardwareTriggeredFlyable(StaticSeqTableTriggerLogic(panda.seq[1]))
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

    for device in devices:
        yield from load_device(
            device, get_device_save_dir(linkam_plan.__name__) / device.__name__
        )
    yield from stamp_temp_pv(
        linkam, stamped_detector, get_ad_xml_dir(linkam_plan.__name__)
    )
    for det in detectors:
        yield from enable_stats_sum(det, get_ad_xml_dir(linkam_plan.__name__))

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_linkam_plan():
        start = trajectory.start
        for segment in trajectory.path:
            start, stop, num = (
                (start, segment.stop, segment.num)
                if segment.num is not None
                else step_to_num(start, segment.stop, segment.step),
            )
            yield from capture_linkam_segment(
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
