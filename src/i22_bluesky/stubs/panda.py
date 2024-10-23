from pathlib import Path

from bluesky.utils import MsgGenerator
from ophyd_async.core import load_device, save_device
from ophyd_async.fastcs.panda import HDFPanda

from i22_bluesky.util.default_devices import PANDA

_SAVES_ROOT = Path(__file__).parent.parent.parent
_LINKAM_FOLDER = "linkam"
_STOPFLOW_FOLDER = "stopflow"


def _get_device_save_dir(plan_name: str) -> Path:
    return _SAVES_ROOT / "pvs" / plan_name


def _save_panda_for_plan(
    plan_name: str, panda: HDFPanda = PANDA, ignore: list[str] | None = None
) -> MsgGenerator:
    ignore = ignore or ["pcap.capture", "data.capture", "data.datasets"]
    yield from save_device(
        panda,
        _get_device_save_dir(plan_name),
        ignore=ignore,
    )


def _load_panda_for_plan(plan_name: str, panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from load_device(
        panda,
        _get_device_save_dir(plan_name),
    )


def save_panda_config_for_stopflow(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from _save_panda_for_plan(_LINKAM_FOLDER, panda)


def load_panda_config_for_stopflow(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from _load_panda_for_plan(_LINKAM_FOLDER, panda)


def save_panda_config_for_linkam(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from _save_panda_for_plan(_STOPFLOW_FOLDER, panda)


def load_panda_config_for_linkam(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from _load_panda_for_plan(_STOPFLOW_FOLDER, panda)
