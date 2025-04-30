from typing import Annotated, Any

import bluesky.preprocessors as bpp
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.common.maths import step_to_num
from dodal.devices.linkam3 import Linkam3
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import StandardDetector, StandardFlyer, YamlSettingsProvider
from ophyd_async.fastcs.panda import HDFPanda, StaticSeqTableTriggerLogic
from ophyd_async.plan_stubs import (
    apply_panda_settings,
    apply_settings,
    retrieve_settings,
    setup_ndstats_sum,
    store_settings,
)
from pydantic import validate_call

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
    get_device_save_dir,
    stamp_temp_pv,
)

DEFAULT_STAMPED_DETECTOR: StandardDetector = inject("saxs")
SETTINGS_FILE_NAME = "linkam.yaml"


def save_linkam(panda: HDFPanda = DEFAULT_PANDA) -> MsgGenerator:
    provider = YamlSettingsProvider(get_device_save_dir(linkam_plan.__name__))
    yield from store_settings(provider, SETTINGS_FILE_NAME, panda)


@attach_data_session_metadata_decorator()
@validate_call(config={"arbitrary_types_allowed": True})
def linkam_plan(
    trajectory: Annotated[LinkamTrajectory, "Trajectory for the scan to follow."],
    linkam: Annotated[Linkam3, "Temperature controller."] = DEFAULT_LINKAM,
    panda: Annotated[
        HDFPanda,
        "Panda with sequence table configured and connected to \
        FastShutter (outa) and each of detectors (outb).",
    ] = DEFAULT_PANDA,
    stamped_detector: Annotated[
        StandardDetector,
        "AreaDetector to configure to stamp the Linkam temperature. \
            Will be automatically added to detectors if not included.",
    ] = DEFAULT_STAMPED_DETECTOR,
    detectors: Annotated[
        set[StandardDetector], "Detectors to capture at each temperature value"
    ] = DEFAULT_DETECTORS,
    shutter_time: Annotated[
        float, "Time allowed for opening shutter before triggering detectors."
    ] = 0.04,
    stream_name: Annotated[str, "Stream name for bluesky documents."] = "primary",
    metadata: dict[str, Any] | None = None,
) -> MsgGenerator:
    """
    Follow a trajectory in temperature, collecting a number of frames either at equally
    spaced positions or while continually scanning. e.g. for 2 segments, the first
    stepped and the 2nd flown:
    trajectory start   v             v final segment stop
                       \\           /
       stepped segment__\\__       /
                           \\     /  flown segment
           1st segment stop \\__ /
        exposures:    xx  xx  xx   1/N seconds
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

    for device in devices:
        provider = YamlSettingsProvider(get_device_save_dir(linkam_plan.__name__))
        settings = yield from retrieve_settings(provider, SETTINGS_FILE_NAME, device)
        if isinstance(device, HDFPanda):
            yield from apply_panda_settings(settings)
        else:
            yield from apply_settings(settings)

    yield from stamp_temp_pv(linkam, stamped_detector)
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
