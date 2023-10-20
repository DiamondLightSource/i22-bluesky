from ophyd_async.epics.areadetector import NDAttributeDataType, NDAttributesXML
from dodal.beamlines.i22 import HDFStatsPilatus
from pathlib import Path


def make_stats_sum_xml(path: Path) -> str:
    xml = NDAttributesXML()
    xml.add_param(
        "STATS_SUM",
        "SUM",
        NDAttributeDataType.DOUBLE,
        description="Sum of each detector frame",
    )
    path.write_text(str(xml))
    return str(path)


def make_saxs_linkam_stamping_xml(path: Path):
    xml = NDAttributesXML()
    xml.add_epics_pv(
        "Temperature",
        "BL22I-EA-TEMPC-01:TEMP",
        description="Current linkam temperature",
    )
    path.write_text(str(xml))
    return str(path)


def load_saxs_linkam_settings(saxs: HDFStatsPilatus, path: Path):
    yield from bps.mv(
        saxs.stats,
        make_stats_sum_xml(path / "stats_sum_stamping.xml"),
        saxs.drv,
        make_saxs_linkam_stamping_xml(path / "drv_linkam_stamping.xml"),
    )
