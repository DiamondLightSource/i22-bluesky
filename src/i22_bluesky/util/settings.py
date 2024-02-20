from pathlib import Path
from typing import Optional

import bluesky.plan_stubs as bps
from dodal.devices.areadetector.pilatus import HDFStatsPilatus
from dodal.devices.tetramm import TetrammDetector
from ophyd_async.core import Device
from ophyd_async.epics.areadetector import NDAttributeDataType, NDAttributesXML


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


def load_pilatus_settings(saxs: HDFStatsPilatus, waxs: HDFStatsPilatus, path: Path):
    xml = make_stats_sum_xml(path / "stats_sum_stamping.xml")
    yield from bps.mv(
        saxs.stats.nd_attributes_file, xml, waxs.stats.nd_attributes_file, xml
    )


def load_tetramm_linkam_settings(linkam: Device, tetramm: TetrammDetector, path: Path):
    xml_path = path / "tetramm_linkam_stamping.xml"
    xml = NDAttributesXML()
    pv = linkam.temp.source.split("://")[1]
    xml.add_epics_pv(
        "Temperature",
        f"{pv}",
        description="Current linkam temperature",
    )
    xml_path.write_text(str(xml))
    yield from bps.mv(
        tetramm.drv.nd_attributes_file,
        str(xml_path),
    )
