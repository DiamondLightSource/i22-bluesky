from ophyd_async.core import Device, walk_rw_signals, set_signal_values, load_from_yaml
from pathlib import Path
from i22_bluesky.util.get_root import get_project_root
from typing import Optional

ROOT_SAVE_DIR = get_project_root() / "pvs"


def load_device(
    device: Device,
    filename_prefix: Optional[str] = None,
) -> None:
    """Loads PV values from a yaml file to a device in-place."""
    device_directory = ROOT_SAVE_DIR / device.__class__.__name__
    filename = device_directory / (
        (device.name if not filename_prefix else filename_prefix) + ".yml"
    )

    if not device_directory.exists():
        raise RuntimeError(
            f"Expected to find {filename} in {device_directory} but {device_directory}"
            + " does not exist! Have you saved this device before?"
        )

    signals = walk_rw_signals(device)
    phases = load_from_yaml(str(device_directory / filename))
    yield from set_signal_values(signals, phases)
