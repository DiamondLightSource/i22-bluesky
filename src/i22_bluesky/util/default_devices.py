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
    saxs(connect_immediately=False),
    waxs(connect_immediately=False),
    i0(connect_immediately=False),
    it(connect_immediately=False),
}

DETECTORS: set[StandardDetector] = FAST_DETECTORS | {oav(connect_immediately=False)}

BASELINE_DEVICES: set[Readable] = {
    fswitch(connect_immediately=False),
    slits_1(connect_immediately=False),
    slits_2(connect_immediately=False),
    slits_3(connect_immediately=False),
    slits_4(connect_immediately=False),
    slits_5(connect_immediately=False),
    slits_6(connect_immediately=False),
    hfm(connect_immediately=False),
    vfm(connect_immediately=False),
    undulator(connect_immediately=False),
    dcm(connect_immediately=False),
    synchrotron(connect_immediately=False),
}

PANDA: HDFPanda = panda1(connect_immediately=False)
LINKAM: Linkam3 = linkam(connect_immediately=False)
STAMPED_DETECTOR: StandardDetector = saxs(connect_immediately=False)
