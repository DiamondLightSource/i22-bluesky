from functools import lru_cache
from pathlib import Path

import bluesky.plan_stubs as bps
from ophyd_async.core import Device
from ophyd_async.epics.areadetector import (
    NDAttributeDataType,
    NDAttributesXML,
    PilatusDetector,
)


@lru_cache(maxsize=1)
def make_stats_sum_xml(path: Path) -> str:
    xml = NDAttributesXML()
    xml.add_param(
        "StatsTotal",
        "TOTAL",
        NDAttributeDataType.DOUBLE,
        description="Sum of each detector frame",
    )
    path.write_text(str(xml))
    return str(path)


@lru_cache(maxsize=1)
def make_saxs_linkam_stamping_xml(linkam: Device, path: Path):
    xml = NDAttributesXML()
    pv = linkam.temp.source.split("://")[1]
    xml.add_epics_pv(
        "Temperature",
        f"{pv}",
        description="Current linkam temperature",
    )
    path.write_text(str(xml))
    return str(path)


def load_saxs_linkam_settings(linkam: Device, saxs: PilatusDetector, path: Path):
    # saxs.stats.nd_attributes_file,
    # make_stats_sum_xml(path / "stats_sum_stamping.xml"),
    yield from bps.mv(
        saxs.drv.nd_attributes_file,
        str(path / "drv_linkam_stamping.xml"),
    )


def load_waxs_settings(waxs: PilatusDetector, path: Path):
    return


# yield from bps.mv(
#         waxs.stats.nd_attributes_file,
#         str(path / "stats_sum_stamping.xml"),
#    ) 
