from ophyd_async.core import Device
from typing import List, Optional
from i22_bluesky.stubs.save import save_device


def save_devices(devices: List[Device], filename_prefix: Optional[str] = None):
    for device in devices:
        yield from save_device(device, filename_prefix=filename_prefix)
