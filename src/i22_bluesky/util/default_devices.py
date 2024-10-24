from bluesky.protocols import Readable
from dodal.beamlines.i22 import (
    dcm,
    fswitch,
    hfm,
    i0,
    it,
    linkam,
    oav,
    panda1,
    saxs,
    slits_1,
    slits_2,
    slits_3,
    slits_4,
    slits_5,
    slits_6,
    synchrotron,
    undulator,
    vfm,
    waxs,
)
from dodal.devices.linkam3 import Linkam3
from ophyd_async.core import StandardDetector
from ophyd_async.fastcs.panda import HDFPanda

FAST_DETECTORS: set[StandardDetector] = {
    saxs(),
    waxs(),
    i0(),
    it(),
}

DETECTORS: set[StandardDetector] = FAST_DETECTORS | {oav()}

BASELINE_DEVICES: set[Readable] = {
    fswitch(),
    slits_1(),
    slits_2(),
    slits_3(),
    slits_4(),
    slits_5(),
    slits_6(),
    hfm(),
    vfm(),
    undulator(),
    dcm(),
    synchrotron(),
}

PANDA: HDFPanda = panda1()
LINKAM: Linkam3 = linkam()
STAMPED_DETECTOR: StandardDetector = saxs()