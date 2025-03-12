from pathlib import Path
from typing import Any

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import bluesky.preprocessors as bpp
from bluesky.protocols import Readable
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.devices.tetramm import TetrammDetector
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import (
    DetectorTrigger,
    StandardDetector,
    StandardFlyer,
    TriggerInfo,
    in_micros,
    YamlSettingsProvider
)
from ophyd_async.fastcs.panda import HDFPanda, StaticSeqTableTriggerLogic
from ophyd_async.fastcs.panda._table import (
    SeqTable,
    SeqTrigger,
)
from ophyd_async.fastcs.panda._trigger import SeqTableInfo
from ophyd_async.plan_stubs import (
    fly_and_collect,
    retrieve_settings,
    apply_panda_settings,
    apply_settings,
)

from i22_bluesky.plans.stopflow import (
    DEADTIME_BUFFER,
    DEFAULT_BASELINE_MEASUREMENTS,
    raise_for_minimum_exposure_times,
)

SETTINGS_FILE_NAME = "pressure_jump.yaml"
XML_PATH = Path("/dls_sw/i22/software/blueapi/scratch/nxattributes")


PRESSURE_JUMP_PANDA_SAVES_DIR = (
    Path(__file__).parent.parent.parent / "pvs" / "pressure_jump" / "panda"
)

FAST_DETECTORS = {
    inject("saxs"),
    inject("waxs"),
    inject("i0"),
    inject("it"),
}

DEFAULT_DETECTORS = FAST_DETECTORS | {inject("oav")}

DEFAULT_PANDA = inject("panda1")

PRESSURE_CELL = inject("pressure_cell")
ROOT_LINKAM_SAVES_DIR = Path(__file__).parent.parent.parent / "pvs" / "linkam_plan"


@attach_data_session_metadata_decorator()
def check_detectors_for_pressure_jump(
    num_frames: int = 1,
    devices: set[Readable] = DEFAULT_DETECTORS | DEFAULT_BASELINE_MEASUREMENTS,
) -> MsgGenerator:
    """
    Take a reading from all devices that are used in the
    pressure jump plan by default
    """

    # Tetramms do not support software triggering
    software_triggerable_devices = {
        device for device in devices if not isinstance(device, TetrammDetector)
    }
    yield from bp.count(
        software_triggerable_devices,
        num=num_frames,
    )


def check_pressure_jump_assembly():
    pass


def pressure_jump(
    start_pressure: float,
    end_pressure: float,
    duration: float,
    exposure: float,
    pre_jump_frames: int = 1,
    post_jump_frames: int = 1,
    shutter_time: float = 4e-3,
    metadata: dict[str, Any] | None = None,
    baseline: set[Readable] = DEFAULT_BASELINE_MEASUREMENTS,
    detectors: set[StandardDetector] = DEFAULT_DETECTORS,
    pressure_cell: StandardDetector = PRESSURE_CELL,
    panda: HDFPanda = DEFAULT_PANDA,
) -> MsgGenerator:
    """
    Perform a pressure jump measurement
    see a detailed description in
    https://github.com/DiamondLightSource/i22-bluesky/issues/79

    Args:
        panda: PandA for controlling flyable motion.
        detectors: A set of detectors that will be collected.
        baseline: A set of devices to be read at the start and end of the plan
            in a stream names baseline.
        start_temp: initial temperature to reach before starting experiment
        cool_temp: target end temp for cooling stage
        cool_step: temperature step dT after each to perform scan
        cool_rate: rate of change of temperature with time, dT/dt
        heat_temp: target end temp for heating stage
        heat_step: temperature step dT after each to perform scan
        heat_rate: rate of change of temperature with time, dT/dt
        num_frames: number of frames to take at each point in temperature
        exposure: exposure time of detectors
        metadata: metadata: Key-value metadata to include in exported data,
            defaults to None.

    Returns:
        MsgGenerator: Plan

    Yields:
        Iterator[MsgGenerator]: Bluesky messages
    """
    # Check that all detectors supplied can actually go as
    # fast as requested
    raise_for_minimum_exposure_times(exposure, detectors)

    stream_name = "main"
    flyer = StandardFlyer(StaticSeqTableTriggerLogic(panda.seq[1]))
    devices = {flyer, panda} | detectors | baseline
    plan_args = {
        "start_pressure": start_pressure,
        "end_pressure": end_pressure,
        "duration": duration,
        "exposure": exposure,
        "panda": panda.name,
        "detectors": {d.name for d in detectors},
        "baseline": {d.name for d in baseline},
    }
    _md = {
        "detectors": {d.name for d in detectors},
        "motors": {pressure_cell.name},
        "plan_args": plan_args,
        "hints": {},
    }
    _md.update(metadata or {})

    for device in detectors:
        provider  = YamlSettingsProvider(ROOT_LINKAM_SAVES_DIR)
        settings = yield from retrieve_settings(provider, SETTINGS_FILE_NAME, device)
        if  isinstance(device, HDFPanda):
            yield from apply_panda_settings(settings)
        else:
            yield from apply_settings(settings)

    @bpp.baseline_decorator(baseline)
    @attach_data_session_metadata_decorator()
    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md=_md)
    def inner_plan():
        provider  = YamlSettingsProvider(PRESSURE_JUMP_PANDA_SAVES_DIR)
        settings = yield from retrieve_settings(provider, SETTINGS_FILE_NAME, panda)
        yield from apply_panda_settings(settings)

        yield from prepare_seq_table_flyer_and_det(
            flyer=flyer,
            detectors=detectors,
            pre_jump_frames=pre_jump_frames,
            post_jump_frames=post_jump_frames,
            exposure=exposure,
            shutter_time=shutter_time,
        )
        yield from fly_and_collect(
            stream_name=stream_name,
            detectors=detectors,
            flyer=flyer,
        )

    rs_uid = yield from inner_plan()
    return rs_uid


# plan utils
def prepare_seq_table_flyer_and_det(
    flyer: StandardFlyer[SeqTableInfo],
    detectors: set[StandardDetector],
    pre_jump_frames: int,
    post_jump_frames: int,
    exposure: float,
    shutter_time: float,
    period: float = 0.0,
) -> MsgGenerator:
    """
    Setup detectors/flyer for a pressure jump experiment. Create a seq table and
    upload it to the panda. Arm all detectors.

    Args:
            flyer: Flyer object that controls the panda
            detectors: Detectors that are triggered by the panda
            post_jump_frames: Number of frames to be collected after the pressure jumps.
            pre_jump_frames: Number of frames (if any) to be collected before
                    the pressure jumps.
            exposure: Detector exposure time
            shutter_time: Time period (seconds) to wait for the shutter to
                    open fully before beginning acquisition
            period: Time period (seconds) to wait after arming the detector
                    before taking the first batch of frames

    Returns:
            MsgGenerator: Plan

    Yields:
            Iterator[MsgGenerator]: Bluesky messages
    """

    deadtime = (
        max(det.controller.get_deadtime(exposure) for det in detectors)
        + DEADTIME_BUFFER
    )
    trigger_info = TriggerInfo(
        num=(pre_jump_frames + post_jump_frames),
        trigger=DetectorTrigger.constant_gate,
        deadtime=deadtime,
        livetime=exposure,
        frame_timeout=60.0,
    )

    # Generate a seq table
    table = pressure_jump_seq_table(
        pre_jump_frames,
        post_jump_frames,
        exposure,
        shutter_time,
        deadtime,
        period,
    )
    table_info = SeqTableInfo(table, repeats=1)

    # Upload the seq table and arm all detectors.
    for det in detectors:
        yield from bps.prepare(det, trigger_info, wait=False, group="prep")
    yield from bps.prepare(flyer, table_info, wait=False, group="prep")
    yield from bps.wait(group="prep")


def pressure_jump_seq_table(
    pre_jump_frames: int,
    post_jump_frames: int,
    exposure: float,
    shutter_time: float,
    deadtime: float,
    period: float,
) -> SeqTable:
    """Create a SeqTable based on the parameters of a a pressure jump measurement

    Args:
            pre_jump_frames: Number of frames to take initially, after pressure jumps
            post_jump_frames: Number of frames to take after pressure jumps
            exposure: Exposure time of each frame (excluding deadtime)
            shutter_time: Time period (seconds) to wait for the shutter
                    to open fully before beginning acquisition
            deadtime: Dead time to leave between frames, dependant on the
                    instruments involved
            period: Time period (seconds) to wait after arming the detector
                    before taking the first batch of frames

    Returns:
            SeqTable: SeqTable that will result in a series of triggers
                    for the measurement
    """

    total_gate_time = (pre_jump_frames + post_jump_frames) * (exposure + deadtime)
    pre_delay = max(period - 2 * shutter_time - total_gate_time, 0)

    # Wait for pre-delay then open shutter
    table = SeqTable(
        time1=in_micros(pre_delay), time2=in_micros(shutter_time), outa2=True
    )

    # Keeping shutter open, do n triggers
    if pre_jump_frames > 0:
        table += SeqTable(
            repeats=pre_jump_frames,
            time1=in_micros(exposure),
            outa1=True,
            outb1=True,
            time2=in_micros(deadtime),
            outa2=True,
        )
    # todo not sure how do we get the trigger exactly
    # Do m triggers after BITA=1
    if post_jump_frames > 0:
        table += SeqTable(
            trigger=SeqTrigger.BITA_1,
            repeats=1,
            time1=in_micros(exposure),
            outa1=True,
            outb1=True,
            time2=in_micros(deadtime),
            outa2=True,
        )
        if post_jump_frames > 1:
            table += SeqTable(
                repeats=post_jump_frames - 1,
                time1=in_micros(exposure),
                outa1=True,
                outb1=True,
                time2=in_micros(deadtime),
                outa2=True,
            )
    # Add the shutter close
    table += SeqTable(time2=in_micros(shutter_time))
    return table
