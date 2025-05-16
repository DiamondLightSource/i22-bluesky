import bluesky.plan_stubs as bps
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.log import LOGGER
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator

from ophyd_async.core import (
    DetectorTrigger,
    TriggerInfo)

from ophyd_async.epics.adaravis import AravisDetector
from ophyd_async.plan_stubs import ensure_connected
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
DEFAULT_TETRAMM = inject("i1")

@attach_data_session_metadata_decorator()
def test_p38_aravis(
    aravis: AravisDetector = DEFAULT_ARAVIS
) -> MsgGenerator:
    pass

@attach_data_session_metadata_decorator()
def test_p38_linkam(
    linkam: Linkam3 = DEFAULT_LINKAM
) -> MsgGenerator:
    yield from bps.mv(linkam, 40)
    data = yield linkam.read()
    LOGGER.info(str(data))

@attach_data_session_metadata_decorator()
def test_p38_pressure_cell(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL
) -> MsgGenerator:
    LOGGER.info("Testing pressure cell...")

    yield from ensure_connected(pressure_cell)
    data = yield from bps.rd(pressure_cell.pressure_transducers[1].omron_pressure)
    #yield from bps.abs_set(pressure_cell.controller.target_pressure, 210)
    #yield from bps.mv(pressure_cell.controller.target_pressure, 210)
    #yield pressure_cell.controller.target_pressure.set(210)
    
    LOGGER.info(str(data))

@attach_data_session_metadata_decorator()
def test_p38_tetramm(
    tetramm: TetrammDetector = DEFAULT_TETRAMM
) -> MsgGenerator:
    LOGGER.info("Testing i1 Tetramm...")
    yield from ensure_connected(tetramm)

    data = yield from bps.rd(tetramm.drv.averaging_time)
    LOGGER.info(str(data))

    yield from bps.mv(tetramm.drv.averaging_time, 0.1)

    data = yield from bps.rd(tetramm.drv.averaging_time)
    LOGGER.info(str(data))



@attach_data_session_metadata_decorator()
def test_p38_tetramm_prepare(
    tetramm: TetrammDetector = DEFAULT_TETRAMM
) -> MsgGenerator:
    LOGGER.info("Testing i1 Tetramm prepare...")
    yield from ensure_connected(tetramm)

    # Values before
    data = yield from bps.rd(tetramm.drv.trigger_mode)
    LOGGER.info(str(data))
    data = yield from bps.rd(tetramm.drv.averaging_time)
    LOGGER.info(str(data))
    data = yield from bps.rd(tetramm.drv.values_per_reading)
    LOGGER.info(str(data))

    trigger_info = TriggerInfo(number_of_triggers=1, 
                        trigger=DetectorTrigger.CONSTANT_GATE, 
                        deadtime=4e-5,
                        livetime=1,
                        multiplier=1,
                        frame_timeout=None)
    
    LOGGER.info("stage tetramm")
    yield from bps.stage_all(tetramm, group="prepare")

    LOGGER.info("prepare tetramm")
    yield from bps.prepare(tetramm, trigger_info, wait=False, group="prepare")

    yield from bps.sleep(0.5)

    yield from bps.wait(group="prepare", timeout=30, error_on_timeout=True)
    LOGGER.info("Prepare complete")

    # Values after
    data = yield from bps.rd(tetramm.drv.trigger_mode)
    LOGGER.info(str(data))
    data = yield from bps.rd(tetramm.drv.averaging_time)
    LOGGER.info(str(data))
    data = yield from bps.rd(tetramm.drv.values_per_reading)
    LOGGER.info(str(data))

    LOGGER.info("tetramm prepare test finished.")