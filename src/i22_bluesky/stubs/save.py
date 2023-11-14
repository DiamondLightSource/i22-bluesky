from pathlib import Path
from typing import List, Optional

from ophyd_async.core import Device, get_signal_values, save_to_yaml, walk_rw_signals

from i22_bluesky.util.get_root import get_project_root

ROOT_SAVE_DIR = get_project_root() / "pvs"


def save_device(
    device: Device,
    filename_prefix: Optional[str] = None,
    ignore_signals: Optional[List[str]] = None,
):
    """Saves PV values to a yaml file, optionally ignoring some signals"""
    signals = walk_rw_signals(device)
    values = yield from get_signal_values(signals, ignore=ignore_signals)
    # units = {n: values.pop(n) for n in list(values) if n.endswith("units")}

    device_directory = ROOT_SAVE_DIR / device.__class__.__name__
    filename = (device.name if not filename_prefix else filename_prefix) + ".yml"

    if not device_directory.exists():
        device_directory.mkdir()

    save_to_yaml([values], str(device_directory / filename))
