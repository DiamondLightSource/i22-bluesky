import bluesky.plans as bp
from bluesky.protocols import Readable
from bluesky.utils import MsgGenerator
from dodal.devices.tetramm import TetrammDetector
from dodal.plans.data_session_metadata import attach_data_session_metadata_decorator
from ophyd_async.plan_stubs import ensure_connected

from i22_bluesky.util.default_devices import (
    BASELINE_DEVICES,
    DETECTORS,
)


@attach_data_session_metadata_decorator()
def check_devices(
    num_frames: int = 1,
    devices: set[Readable] = DETECTORS | BASELINE_DEVICES,
) -> MsgGenerator:
    """
    Take a reading from default devices to ensure they are able to connect and
    capture data.
    """

    # Tetramms do not support software triggering
    software_triggerable_devices = {
        device for device in devices if not isinstance(device, TetrammDetector)
    }
    yield from ensure_connected(*software_triggerable_devices)
    yield from bp.count(
        tuple(software_triggerable_devices),
        num=num_frames,
    )
