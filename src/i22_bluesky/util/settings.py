from functools import lru_cache
from pathlib import Path

import bluesky.plan_stubs as bps
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import StandardDetector
from ophyd_async.epics.areadetector import NDAttributeDataType, NDAttributesXML
from ophyd_async.epics.areadetector.drivers import ADBase

SAVES_ROOT = Path(__file__).parent.parent.parent


def get_device_save_dir(plan_name: str) -> Path:
    return SAVES_ROOT / f"pvs/{plan_name}"


def get_ad_xml_dir(plan_name: str) -> Path:
    return SAVES_ROOT / f"xml/{plan_name}"


@lru_cache(maxsize=1)
def _enable_stats_sum_xml() -> NDAttributesXML:
    xml = NDAttributesXML()
    xml.add_param(
        "StatsTotal",
        "TOTAL",
        NDAttributeDataType.DOUBLE,
        description="Sum of each detector frame",
    )
    return xml


@lru_cache(maxsize=1)
def _enable_pv_stamping(name: str, pv: str, description: str) -> NDAttributesXML:
    xml = NDAttributesXML()
    xml.add_epics_pv(name, pv, description=description)
    return xml


@lru_cache(maxsize=1)
def path_stats_sum_enabled(base_path: Path) -> str:
    path = base_path / "stats_sum_stamping.xml"
    path.write_text(str(_enable_stats_sum_xml()))
    return str(path)


@lru_cache(maxsize=1)
def path_temp_stamping_enabled(linkam: Linkam3, base_path: Path):
    path = base_path / "drv_linkam_stamping.xml"
    path.write_text(
        str(
            _enable_pv_stamping(
                "Temperature",
                linkam.temp.source.split("://")[1],
                "Current linkam temperature",
            )
        )
    )
    return str(path)


def stamp_temp_pv(linkam: Linkam3, stamped_detector: StandardDetector, base_path: Path):
    assert isinstance(driver := stamped_detector.drv, ADBase)
    yield from bps.mv(
        driver.nd_attributes_file,
        path_temp_stamping_enabled(linkam, base_path),
    )


def enable_stats_sum(detector: StandardDetector, base_path: Path):
    assert isinstance(stats := detector.stats, ADBase)
    yield from bps.mv(
        stats.nd_attributes_file,
        path_stats_sum_enabled(base_path),
    )
