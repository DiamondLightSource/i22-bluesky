import bluesky.plan_stubs as bps
from dodal.common import MsgGenerator, inject
from dodal.devices.pressure_jump_cell import (
    FastValveControlRequest,
    PressureJumpCell,
    PumpMotorControlRequest,
)

DEFAULT_PRESSURE_CELL = inject("high_pressure_xray_cell")


def make_popping_sound(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL,
) -> MsgGenerator:
    # set V3 to open
    # pressure_cell.all_valves_control.fast_valve_control[3].set(FastValveControlRequest.OPEN)  # noqa: E501
    # set V5 or V6 to open
    # pressure_cell.all_valves_control.valve_control[5].set(ValveControlRequest.OPEN)
    yield from bps.mv(pressure_cell, 0)
    # todo expect the pressure to rise
    readout = pressure_cell.cell_temperature.read()
    print(f"readout: {readout}")
    # ok but which pressure transducer?
    yield from bps.collect(pressure_cell.pressure_transducers[1], name="omron_pressure")


def lower_pressure(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL,
    target_pressure: float = 10,
) -> MsgGenerator:
    readout = yield pressure_cell.pressure_transducers[3].omron_pressure.read()
    if readout < target_pressure:
        yield from ({})
    """
    for lower 6 must be open
    """
    # todo not sure what is the difference exactly
    # yield from bps.read(pressure_cell.all_valves_control.set_valve(6, FastValveControlRequest.OPEN))
    yield pressure_cell.all_valves_control.set_valve(6, FastValveControlRequest.OPEN)
    # the pressure lowering itself
    yield pressure_cell.pump.pump_motor_direction(PumpMotorControlRequest.REVERSE)
    yield pressure_cell.pump.pump_position.set(target_pressure)

    # in intervals check the pressure until reaches the target pressure
    while readout > target_pressure:
        # todo consider adding just read_cell method on the cell to read the omron pressure at the third transducer
        readout = yield from bps.read(
            pressure_cell.pressure_transducers[3], "omron_pressure"
        )

    assert target_pressure >= readout


def raise_pressure(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL,
    target_pressure: float = 1000,
) -> MsgGenerator:
    """
    for raise 5 must be open

    """
    yield pressure_cell.all_valves_control.set_valve(5, FastValveControlRequest.OPEN)

    # the pressure raising itself
    yield pressure_cell.pump.pump_motor_direction(PumpMotorControlRequest.FORWARD)
    pressure_cell.pump.pump_position.set(target_pressure)
    readout = yield pressure_cell.pressure_transducers[3].omron_pressure.read()

    # in intervals check the pressure until reaches the target pressure
    while readout < target_pressure:
        readout = yield pressure_cell.pressure_transducers[3].omron_pressure.read()

    assert readout >= target_pressure


# preparation stage
async def prepare_pressure_cell(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL,
):
    # pressure 1 and 3 must be less than 50 bar
    # one connects the pump to the

    pressure_cell.all_valves_control.fast_valve_control[3].set()
    # todo not sure if need to add pressure readouts at the valves in the device
