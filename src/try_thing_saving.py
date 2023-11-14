from dodal.beamlines import i22
from bluesky import RunEngine
from ophyd_async.core import DeviceCollector
from i22_bluesky.stubs.save import save_device
from i22_bluesky.stubs.load import load_device
import bluesky.plan_stubs as bps

if __name__ == "__main__":
    RE = RunEngine()
    with DeviceCollector():
        tetram1 = i22.tetramm1()
        tetram2 = i22.tetramm2()
        panda = i22.panda()
        linkam = i22.linkam()
        saxs = i22.saxs()
        waxs = i22.waxs()

    # RE(
    #     save_device(
    #         panda, ignore_signals=["seq1.table"], filename_prefix="no_unit_distinction"
    #     )
    # )
    RE(bps.abs_set(tetram2.hdf.compression.set("szip")))
    RE(bps.abs_set(tetram2.drv.bias_volts.set(9.6)))
    # RE(save_device(linkam))

    # RE(load_device(panda2))

    print()
