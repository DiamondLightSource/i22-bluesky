import bluesky.plan_stubs as bps
from dodal.common import MsgGenerator, inject
from dodal.devices.pressure_cell import PressureCell


def test_pressure_cell() -> MsgGenerator:
    yield from {}


DEFAULT_PRESSURE_CELL = inject("high_pressure_xray_cell")


def make_popping_sound(
    pressure_cell: PressureCell = DEFAULT_PRESSURE_CELL,
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
