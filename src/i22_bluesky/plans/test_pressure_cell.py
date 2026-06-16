import bluesky.plan_stubs as bps
from bluesky.utils import MsgGenerator
from dodal.devices.pressure_jump_cell import (
    FastValveControlRequest,
    PressureJumpCell,
)

from i22_bluesky.util.baseline import DEFAULT_PRESSURE_CELL


def make_popping_sound(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL,
) -> MsgGenerator:
    # set V3 to open
    pressure_cell.all_valves_control.fast_valve_control[3].set(
        FastValveControlRequest.OPEN
    )  # noqa: E501
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
    readout = yield from bps.read(pressure_cell.pressure_transducers[3].omron_pressure)
    if readout < target_pressure:
        yield from ({})
    """
    for lower 6 must be open
    """
    yield from bps.mv(
        pressure_cell.all_valves_control.valve_control[6], FastValveControlRequest.OPEN
    )

    # the pressure lowering itself
    yield from bps.mv(pressure_cell.control, target_pressure)

    # in intervals check the pressure until reaches the target pressure
    while readout > target_pressure:
        # todo consider adding just read_cell method on the cell
        # to read the omron pressure at the third transducer
        readout = yield from bps.read(
            pressure_cell.pressure_transducers[3].omron_pressure
        )

    assert target_pressure >= readout


def raise_pressure(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL,
    target_pressure: float = 1000,
) -> MsgGenerator:
    """
    for raise 5 must be open

    """
    yield from bps.mv(
        pressure_cell.all_valves_control.valve_control[5], FastValveControlRequest.OPEN
    )

    # the pressure raising itself
    yield from bps.mv(pressure_cell.control, target_pressure)

    readout = yield from bps.read(pressure_cell.pressure_transducers[3].omron_pressure)

    # in intervals check the pressure until reaches the target pressure
    while readout < target_pressure:
        readout = yield from bps.rd(
            pressure_cell.pressure_transducers[3].omron_pressure
        )

    assert readout >= target_pressure


# preparation stage
async def prepare_pressure_cell(
    pressure_cell: PressureJumpCell = DEFAULT_PRESSURE_CELL,
):
    # pressure 1 and 3 must be less than 50 bar
    # one connects the pump to the

    # todo not sure if need to add pressure readouts at the valves in the device
    pass
