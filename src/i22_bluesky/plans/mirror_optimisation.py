import random as rand

import bluesky.preprocessors as bpp
from bluesky import plan_stubs as bps
from bluesky.utils import MsgGenerator
from dodal.devices.bimorph_mirror import BimorphMirror
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import StandardDetector

# 32 channels in vertical axis
# 12 channels in horizontal axis
# +/- 500 Volt range in each channel
# Can't have more than a 500V difference between neighbouring channels
# 3000 iterations of the Adam algorithm per fold

data_collection_size = 100


def get_random_channel(mirror: BimorphMirror) -> int:
    return rand.choice(list(mirror.channels))


def next_all_channels(vfm: BimorphMirror, hfm: BimorphMirror) -> MsgGenerator:
    """
    stub - randomly moves voltages in all channels
    """
    yield from bps.mv(vfm, {v: rand.uniform(-500, 500) for v in vfm.channels.keys()})
    yield from bps.mv(hfm, {v: rand.uniform(-500, 500) for v in hfm.channels.keys()})


def next_single_channel(vfm: BimorphMirror, hfm: BimorphMirror) -> MsgGenerator:
    """
    stub - randomly moves voltage in a single channel
    """
    yield from bps.mv(vfm, {get_random_channel(vfm): rand.uniform(-500, 500)})
    yield from bps.mv(hfm, {get_random_channel(hfm): rand.uniform(-500, 500)})


def next_mixed_channel(vfm: BimorphMirror, hfm: BimorphMirror) -> MsgGenerator:
    """
    stub - randomly moves voltages across a varying number of channels
    """
    vx = get_random_channel(vfm)
    vy = get_random_channel(vfm)
    if vy > vx:
        vx, vy = vy, vx
    hx = get_random_channel(hfm)
    hy = get_random_channel(hfm)
    if hy > hx:
        hx, hy = hy, hx
    yield from bps.mv(vfm, {v: rand.uniform(-500, 500) for v in range(vx, vy)})
    yield from bps.mv(hfm, {v: rand.uniform(-500, 500) for v in range(hx, hy)})


def good_mirror_config(vfm: BimorphMirror, hfm: BimorphMirror) -> MsgGenerator:
    """
    stub - return bimorph mirror to known configuration
    """
    yield from bps.mv(vfm, {v: rand.random(-500, 500) for v in vfm.channels.keys()})
    yield from bps.mv(hfm, {v: rand.random(-500, 500) for v in hfm.channels.keys()})


@attach_data_session_metadata_decorator()
def bimorph_mirror_data_collection(
    vfm: BimorphMirror, hfm: BimorphMirror, detectors: set[StandardDetector]
) -> MsgGenerator:
    """
    plan - move the vertical and horizonal bimorph mirrors by random amounts

    Will randomly create datasets with the following:
    - Just single channel movements
    - Move all channels at once
    - Move all channels sometimes, otherwise alter single channels
    """
    devices = [vfm, hfm, *detectors]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator()
    def innerplan():
        # Do split 40% of the time
        if rand.uniform(0, 9) <= 5:
            for _ in range(data_collection_size):
                # 60%
                if rand.uniform(0, 9) <= 7:
                    yield from next_mixed_channel(vfm, hfm)
                elif rand.uniform(0, 9) <= 6:
                    # 20%
                    yield from next_single_channel(vfm, hfm)
                else:
                    # 20%
                    yield from next_all_channels(vfm, hfm)
                yield from bps.trigger_and_read(*devices)  # data out
        # 20%
        elif rand.uniform(0, 9) <= 3:
            for _ in range(data_collection_size):
                yield from next_all_channels(vfm, hfm)
                yield from bps.trigger_and_read(*devices)
        # 20%
        elif rand.uniform(0, 9) <= 3:
            for _ in range(data_collection_size):
                yield from next_mixed_channel(vfm, hfm)
                yield from bps.trigger_and_read(*devices)
        # 20%
        else:
            for _ in range(data_collection_size):
                yield from next_single_channel(vfm, hfm)
                yield from bps.trigger_and_read(*devices)

    yield from innerplan()


@attach_data_session_metadata_decorator()
def bimorph_cleanup(
    mirror: BimorphMirror, detectors: set[StandardDetector]
) -> MsgGenerator:
    """
    plan - return to known mirror configuration
    """
    devices = [mirror, *detectors]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator()
    def innerplan():
        for _ in range(data_collection_size):
            yield from good_mirror_config(mirror)
            yield from bps.trigger_and_read(*devices)

    yield from innerplan()


@attach_data_session_metadata_decorator()
def mirror_output(mirror: BimorphMirror) -> MsgGenerator:
    """
    plan - print the dict of all channel voltages
    """

    @bpp.stage_decorator([mirror])
    @bpp.run_decorator()
    def innerplan():
        yield from bps.trigger_and_read([mirror])

    yield from innerplan()


#
@attach_data_session_metadata_decorator()
def optimise_bimorph(
    vfm: BimorphMirror, hfm: BimorphMirror, detectors: set[StandardDetector]
) -> MsgGenerator:
    devices = [vfm, hfm, *detectors]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator()
    def innerplan():
        pass

    yield from innerplan()
