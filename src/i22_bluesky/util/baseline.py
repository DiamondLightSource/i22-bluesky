from bluesky.protocols import Readable
from dodal.common import inject
from ophyd_async.core import StandardDetector
from ophyd_async.panda import HDFPanda

FAST_DETECTORS: set[StandardDetector] = {
    inject("saxs"),
    inject("waxs"),
    inject("i0"),
    inject("it"),
}

DEFAULT_DETECTORS: set[StandardDetector] = FAST_DETECTORS | {inject("oav")}

DEFAULT_BASELINE_MEASUREMENTS: set[Readable] = {
    inject("fswitch"),
    inject("slits_1"),
    inject("slits_2"),
    inject("slits_3"),
    # inject("slits_4"), Until we make this device
    inject("slits_5"),
    inject("slits_6"),
    inject("hfm"),
    inject("vfm"),
    inject("undulator"),
    inject("dcm"),
    inject("synchrotron"),
}

DEFAULT_PANDA: HDFPanda = inject("panda1")
