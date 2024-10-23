from pathlib import Path

from bluesky.utils import MsgGenerator
from ophyd_async.core import load_device, save_device
from ophyd_async.fastcs.panda import HDFPanda

from i22_bluesky.util.default_devices import PANDA

SAVES_ROOT = Path(__file__).parent.parent.parent
LINKAM_FOLDER = "linkam"
STOPFLOW_FOLDER = "stopflow"


def get_device_save_dir(plan_name: str) -> Path:
    return SAVES_ROOT / "pvs" / plan_name


def save_panda_for_plan(
    plan_name: str, panda: HDFPanda = PANDA, ignore: list[str] | None = None
) -> MsgGenerator:
    ignore = ignore or ["pcap.capture", "data.capture", "data.datasets"]
    yield from save_device(
        panda,
        get_device_save_dir(plan_name),
        ignore=ignore,
    )


def load_panda_for_plan(plan_name: str, panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from load_device(
        panda,
        get_device_save_dir(plan_name),
    )


def save_panda_config_for_stopflow(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from save_panda_for_plan(LINKAM_FOLDER, panda)


def load_panda_config_for_stopflow(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from load_panda_for_plan(LINKAM_FOLDER, panda)


def save_panda_config_for_linkam(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from save_panda_for_plan(STOPFLOW_FOLDER, panda)


def load_panda_config_for_linkam(panda: HDFPanda = PANDA) -> MsgGenerator:
    yield from load_panda_for_plan(STOPFLOW_FOLDER, panda)
