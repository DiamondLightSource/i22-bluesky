import bluesky.plan_stubs as bps
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.log import LOGGER

from ophyd_async.epics.adaravis import AravisDetector
from dodal.devices.linkam3 import Linkam3
from dodal.devices.pressure_jump_cell import (
    FastValveControlRequest,
    PressureJumpCell,
    PumpMotorDirectionState,
)
from dodal.devices.tetramm import TetrammDetector



DEFAULT_ARAVIS = inject("d11")
DEFAULT_LINKAM = inject("linkam")
DEFAULT_PRESSURE_CELL = inject("high_pressure_xray_cell")
DEFAULT_TETRAMM = inject("i0")


def test_p38_aravis(
    aravis: AravisDetector = DEFAULT_ARAVIS
) -> MsgGenerator:
    pass

def test_p38_linkam(
    linkam: Linkam3 = DEFAULT_LINKAM
) -> MsgGenerator:
    yield from bps.mv(linkam, 40)
    data = yield linkam.read()
    LOGGER.info(str(data))

def test_p38_pressure_cell(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL
) -> MsgGenerator:
    pass

def test_p38_tetramm(
    tetramm: TetrammDetector = DEFAULT_TETRAMM
) -> MsgGenerator:
    data = yield tetramm.read()
    LOGGER.info(str(data))

