import os
from pathlib import Path

from dls_bluesky_core.core import MsgGenerator
from ophyd_async.core import (
    Device,
    get_signal_values,
    load_from_yaml,
    save_to_yaml,
    set_signal_values,
    walk_rw_signals,
)

from i22_bluesky.util.get_root import get_project_root

ROOT_SAVE_DIR = get_project_root() / "pvs"


def save(
    devices: set[Device], config_id: str, ignore_signals: set[str] | None = None
) -> MsgGenerator:
    for device in devices:
        yield from save_device(device, config_id, ignore_signals)


def load(devices: set[Device], config_id: str) -> MsgGenerator:
    for device in devices:
        yield from load_device(device, config_id)


def save_device(
    device: Device, config_id: str, ignore_signals: set[str] | None = None
) -> MsgGenerator:
    signals = walk_rw_signals(device)
    values = yield from get_signal_values(signals, ignore=ignore_signals or {})

    # Pretend we have a database, which would be sensible, but it's actually files
    device_directory = _device_directory(device, config_id)
    file_name = device.name + ".yml"
    file_path = device_directory / file_name

    if not device_directory.exists():
        os.makedirs(device_directory)

    save_to_yaml([values], str(file_path))


def load_device(device: Device, config_id: str) -> MsgGenerator:
    # Pretend we have a database, which would be sensible, but it's actually files
    device_directory = _device_directory(device, config_id)
    file_name = device.name + ".yml"
    file_path = device_directory / file_name

    if not device_directory.exists():
        raise KeyError(
            f"Expected to find {file_name} in {device_directory} but {device_directory}"
            + " does not exist! Have you saved this device before?"
        )
    elif not file_path.exists():
        raise KeyError(
            f"Expected to find {file_path} in {device_directory} but it"
            + " does not exist! Have you saved this device before?"
        )

    signals = walk_rw_signals(device)
    phases = load_from_yaml(str(file_path))
    yield from set_signal_values(signals, phases)


def _device_directory(device: Device, config_id: str) -> Path:
    return ROOT_SAVE_DIR / config_id / device.__class__.__name__ / device.name
