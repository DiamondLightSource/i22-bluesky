import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp
from bluesky.utils import MsgGenerator
from dodal.common import inject
from dodal.log import LOGGER
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator

from ophyd_async.core import (
    DetectorTrigger,
    TriggerInfo)

from ophyd_async.epics.adaravis import AravisDetector
from ophyd_async.plan_stubs import ensure_connected, fly_and_collect
from dodal.devices.linkam3 import Linkam3
from dodal.devices.pressure_jump_cell import (
    FastValveControlRequest,
    PressureJumpCell,
    PumpMotorDirectionState,
)
from dodal.devices.areadetector import PressureJumpCellDetector
from dodal.devices.areadetector.pressurejumpcell_io import ( AdcTriggerState )
from dodal.devices.tetramm import TetrammDetector
from dodal.plan_stubs.pressure_jump_cell import prepare_fast_pressure_jump


DEFAULT_ARAVIS = inject("d11")
DEFAULT_LINKAM = inject("linkam")
DEFAULT_PRESSURE_CELL = inject("high_pressure_xray_cell")
DEFAULT_PRESSURE_CELL_AD = inject("high_pressure_xray_cell_adc")
DEFAULT_TETRAMM = inject("i1")

def debug_log_pcell_pressures(pcell: PressureJumpCell):
    data = yield from bps.rd(pcell.pressure_transducers[1].omron_pressure)
    LOGGER.info("T1: " + str(data))

    data = yield from bps.rd(pcell.pressure_transducers[2].omron_pressure)
    LOGGER.info("T2: " + str(data))

    data = yield from bps.rd(pcell.pressure_transducers[3].omron_pressure)
    LOGGER.info("T3: " + str(data))

@attach_data_session_metadata_decorator()
def test_p38_aravis(
    aravis: AravisDetector = DEFAULT_ARAVIS
) -> MsgGenerator:
    pass

@attach_data_session_metadata_decorator()
def test_p38_linkam(
    linkam: Linkam3 = DEFAULT_LINKAM
) -> MsgGenerator:
    LOGGER.info("Testing linkam...")
    yield from ensure_connected(linkam)
    data = yield from bps.rd(linkam.temp)
    LOGGER.info(str(data))

    yield from bps.mv(linkam, 27)
    data = yield from bps.rd(linkam.temp)
    LOGGER.info(str(data))

    yield from bps.mv(linkam, 40)
    data = yield from bps.rd(linkam.temp)
    LOGGER.info(str(data))

    data = yield linkam.read()
    LOGGER.info(str(data))

    yield from bps.mv(linkam, 25)


@attach_data_session_metadata_decorator()
def test_p38_linkam_scan(
    linkam: Linkam3 = DEFAULT_LINKAM
) -> MsgGenerator:
    LOGGER.info("Testing linkam scan...")
    yield from ensure_connected(linkam)
    data = yield from bps.rd(linkam.temp)
    LOGGER.info(str(data))

    yield from bps.mv(linkam, 27)
    data = yield from bps.rd(linkam.temp)
    LOGGER.info(str(data))

    yield from bps.mv(linkam, 40)
    data = yield from bps.rd(linkam.temp)
    LOGGER.info(str(data))

    data = yield linkam.read()
    LOGGER.info(str(data))

    yield from bps.mv(linkam, 25)


@attach_data_session_metadata_decorator()
def test_p38_pressure_cell(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL
) -> MsgGenerator:
    LOGGER.info("Testing pressure cell...")
    yield from ensure_connected(pressure_cell)

    data = yield from bps.rd(pressure_cell.pressure_transducers[1].omron_pressure)
    LOGGER.info("T1: " + str(data))

    data = yield from bps.rd(pressure_cell.control.target_pressure)
    LOGGER.info("Ptarget: " + str(data))

    data = yield from bps.rd(pressure_cell.control.timeout)
    LOGGER.info("timeout: " + str(data))

    yield from bps.mv(pressure_cell.control.target_pressure, 150)
    yield from bps.mv(pressure_cell.control.go, True)

    data = yield from bps.rd(pressure_cell.control.target_pressure)
    LOGGER.info("Ptarget: " + str(data))

    data = yield from bps.rd(pressure_cell.control.result)
    LOGGER.info("Result: " +str(data))

    data = yield from bps.rd(pressure_cell.pressure_transducers[1].omron_pressure)
    LOGGER.info("T1: " +str(data))


@attach_data_session_metadata_decorator()
def test_p38_pressure_cell_pressure(
    pressure: int,
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL
) -> MsgGenerator:
    LOGGER.info(f"Testing pressure cell pressure = {pressure} ...")

    yield from ensure_connected(pressure_cell)

    yield from debug_log_pcell_pressures(pressure_cell)

    data = yield from bps.rd(pressure_cell.control.timeout)
    LOGGER.info("timeout: " + str(data))

    data = yield from bps.rd(pressure_cell.control.busy)
    LOGGER.info("busy: " + str(data))

    # Set the pressure
    yield from bps.mv(pressure_cell.control, pressure)

    LOGGER.info("pressure mv end")

    data = yield from bps.rd(pressure_cell.control.busy)
    LOGGER.info("busy: " + str(data))

    data = yield from bps.rd(pressure_cell.control.result)
    LOGGER.info("Result: " +str(data))

    yield from debug_log_pcell_pressures(pressure_cell)


@attach_data_session_metadata_decorator()
def test_p38_pressure_cell_jump(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL
) -> MsgGenerator:
    LOGGER.info("Testing pressure cell...")

    yield from ensure_connected(pressure_cell)

    yield from debug_log_pcell_pressures(pressure_cell)

    data = yield from bps.rd(pressure_cell.control.timeout)
    LOGGER.info("timeout: " + str(data))

    yield from bps.mv(pressure_cell.control.from_pressure, 150)
    yield from bps.mv(pressure_cell.control.to_pressure, 170)

    data = yield from bps.rd(pressure_cell.control.from_pressure)
    LOGGER.info("Pjump-from: " + str(data))

    data = yield from bps.rd(pressure_cell.control.to_pressure)
    LOGGER.info("Pjump-to: " + str(data))

    # START the jump
    yield from bps.mv(pressure_cell.control.jump_ready, True)

    data = yield from bps.rd(pressure_cell.control.result)
    LOGGER.info("Result: " +str(data))

    debug_log_pcell_pressures(pressure_cell)


@attach_data_session_metadata_decorator()
def test_p38_pressure_cell_setup_trigger(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL,
    pressure_cell_ad: PressureJumpCellDetector = DEFAULT_PRESSURE_CELL_AD
) -> MsgGenerator:
    LOGGER.info("Testing pressure cell trigger...")

    yield from ensure_connected(pressure_cell)

    yield from debug_log_pcell_pressures(pressure_cell)

    data = yield from bps.rd(pressure_cell.control.timeout)
    LOGGER.info("timeout: " + str(data))


    # Arm and start waiting for trigger
    data = yield from bps.rd(pressure_cell_ad.trig.state)
    LOGGER.info("trig-state: " + str(data))

    yield from bps.abs_set(pressure_cell_ad.trig.capture, True)

    data = yield from bps.rd(pressure_cell_ad.trig.state)
    LOGGER.info("trig-state: " + str(data))

    trigger_state = yield from bps.rd(pressure_cell_ad.trig.state) 

    while (trigger_state != AdcTriggerState.IDLE):
        LOGGER.info("trig-state: " + str(data))
        trigger_state = yield from bps.rd(pressure_cell_ad.trig.state)
        yield from bps.sleep(0.2)

    yield from debug_log_pcell_pressures(pressure_cell)


@attach_data_session_metadata_decorator()
def test_p38_pressure_cell_fast_jump(
    pressure_from: int,
    pressure_to: int,
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL,
    pressure_cell_ad: PressureJumpCellDetector = DEFAULT_PRESSURE_CELL_AD,

) -> MsgGenerator:
    ensure_connected(pressure_cell)

    @bpp.run_decorator()
    @bpp.stage_decorator([pressure_cell, pressure_cell])
    def inner() -> MsgGenerator:
        LOGGER.info(f"Testing pressure cell fast jump, from {pressure_from} to {pressure_to}...")

        yield from debug_log_pcell_pressures(pressure_cell)

        trigger_info = TriggerInfo(
            trigger= DetectorTrigger.INTERNAL
        )

        # Setup
        yield from prepare_fast_pressure_jump(pressure_cell, pressure_from, pressure_to)

        yield from bps.prepare(pressure_cell_ad, trigger_info, group="prepare")

        # Fly and collect
        yield from bps.declare_stream(pressure_cell_ad, name="main", collect=True)
        yield from bps.kickoff(pressure_cell_ad)
        yield from bps.complete(pressure_cell_ad)

        yield from debug_log_pcell_pressures(pressure_cell)
    yield from inner()


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
