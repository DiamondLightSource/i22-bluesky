from pathlib import Path

from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import StandardDetector
from ophyd_async.epics.adcore import (
    ADBaseIO,
    NDAttributePv,
    NDAttributePvDbrType,
)
from ophyd_async.plan_stubs import setup_ndattributes

SAVES_ROOT = Path(__file__).parent.parent.parent


def get_device_save_dir(plan_name: str) -> Path:
    return SAVES_ROOT / "pvs" / plan_name


def stamp_temp_pv(linkam: Linkam3, stamped_detector: StandardDetector):
    assert isinstance(driver := stamped_detector.drv, ADBaseIO)
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
