
import bluesky.plan_stubs as bps
from dodal.common import MsgGenerator, inject


from dodal.devices.pressure_cell import PressureCell


def test_pressure_cell()-> MsgGenerator:
    yield from {}


def make_popping_sound() -> MsgGenerator:
    yield from bps.mv(pressure_cell, 0)
