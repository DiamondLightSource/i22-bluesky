from pathlib import Path

from bluesky.utils import MsgGenerator
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import Device, StandardDetector, YamlSettingsProvider
from ophyd_async.epics.adcore import (
    ADBaseController,
    ADBaseIO,
    NDAttributePv,
    NDAttributePvDbrType,
)
from ophyd_async.fastcs.panda import HDFPanda
from ophyd_async.plan_stubs import retrieve_settings, setup_ndattributes, store_settings

_REPO_ROOT = Path(__file__).parent.parent.parent.parent

_SETTINGS_PROVIDER = YamlSettingsProvider(_REPO_ROOT / "pvs")


def save_device(device: Device, plan_name: str) -> MsgGenerator:
    yield from store_settings(
        _SETTINGS_PROVIDER, plan_name, device, only_config=isinstance(device, HDFPanda)
    )


def load_device(device: Device, plan_name: str) -> MsgGenerator:
    yield from retrieve_settings(
        _SETTINGS_PROVIDER, plan_name, device, only_config=isinstance(device, HDFPanda)
    )


def stamp_temp_pv(linkam: Linkam3, stamped_detector: StandardDetector):
    controller = stamped_detector._controller  # noqa: SLF001
    if isinstance(controller, ADBaseController) and isinstance(
        driver := controller.driver, ADBaseIO
    ):
        yield from setup_ndattributes(
            driver,
            [
                NDAttributePv(
                    "Temperature",
                    linkam.temp,
                    dbrtype=NDAttributePvDbrType.DBR_FLOAT,
                    description="Current linkam temperature",
                )
            ],
        )
