from bluesky.protocols import Readable
from dodal.common import inject
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import StandardDetector
from ophyd_async.fastcs.panda import HDFPanda

FAST_DETECTORS: set[StandardDetector] = {
    inject("saxs"),
    inject("waxs"),
    # inject("i0"),
    # inject("it"),
}
DEFAULT_STAMPED_DETECTOR: StandardDetector = inject("saxs")

DEFAULT_DETECTORS: set[StandardDetector] = FAST_DETECTORS | {inject("oav")}

DEFAULT_BASELINE_MEASUREMENTS: set[Readable] = {
    inject("fswitch"),
    inject("slits_1"),
    inject("slits_2"),
    inject("slits_3"),
    inject("slits_4"),
    inject("slits_5"),
    inject("slits_6"),
    inject("hfm"),
    inject("vfm"),
    inject("undulator"),
    inject("dcm"),
    inject("synchrotron"),
}

#: Buffer added to deadtime to handle minor discrepencies between detector
#: and panda clocks
DEADTIME_BUFFER = 20e-6

DEFAULT_PANDA: HDFPanda = inject("panda1")
DEFAULT_LINKAM: Linkam3 = inject("linkam")
DEFAULT_PRESSURE_CELL = inject("pressure_cell")
