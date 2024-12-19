import random as rand

import bluesky.preprocessors as bpp
from bluesky import plan_stubs as bps
from bluesky.utils import MsgGenerator
from dodal.devices.bimorph_mirror import BimorphMirror
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import StandardDetector

# 3000 iterations of the Adam algorithm per fold

data_collection_size = 100


def get_random_channel(mirror: BimorphMirror) -> int:
    return rand.choice(list(mirror.channels))


def evaluate_volt_diff_all_channels(mirror: dict[int, float]) -> None:
    for index in mirror:
        if index + 1 in mirror:
            channel_diff = mirror[index] - mirror[index + 1]
            print(f"channel_diff: {channel_diff}")
            if abs(channel_diff) >= 500:
                mirror[index + 1] = mirror[index + 1] // 3


def next_all_channels(vfm: BimorphMirror, hfm: BimorphMirror) -> MsgGenerator:
    """
    stub
    ---
    Increment all channels by small amount and check physics of the system:
     - +/- 500 Volt range in each channel
     - Can't have more than a 500V difference between neighbouring channels.
    """

    vfm_prev = {}
    vfm_next = {}
    for index, channel in vfm.channels.items():
        step = rand.uniform(-20, 20)
        vfm_prev[index] = yield from bps.rd(channel)
        if abs(vfm_prev[index] + step) >= 500:
            vfm_next[index] = vfm_prev[index] - step
        else:
            vfm_next[index] = vfm_prev[index] + step

    evaluate_volt_diff_all_channels(vfm_next)

    # Repeat for the hfm channels
    hfm_prev = {}
    hfm_next = {}
    for index, channel in hfm.channels.items():
        step = rand.uniform(-20, 20)
        hfm_prev[index] = yield from bps.rd(channel)
        if abs(hfm_prev[index] + step) >= 500:
            hfm_next[index] = hfm_prev[index] - step
        else:
            hfm_next[index] = hfm_prev[index] + step

    evaluate_volt_diff_all_channels(hfm_next)

    yield from bps.mv(vfm, vfm_next)
    yield from bps.mv(hfm, hfm_next)


def next_single_channel(vfm: BimorphMirror, hfm: BimorphMirror) -> MsgGenerator:
    """
    stub
    ---
    Increment a channel by small amount and check physics of the system:
     - +/- 500 Volt range in each channel
     - Can't have more than a 500V difference between neighbouring channels.
    """

    vfm_prev = {}

    for index, channel in vfm.channels.items():
        vfm_prev[index] = yield from bps.rd(channel)
    vfm_next = {**vfm_prev}

    rand_channel = get_random_channel(vfm)
    # step = rand.uniform(-20, 20)
    step = rand.uniform(-200, 200)
    vfm_prev[rand_channel] = yield from bps.rd(vfm.channels[rand_channel])
    if abs(vfm_prev[rand_channel] + step) >= 500:
        vfm_next[rand_channel] = vfm_prev[rand_channel] - step
    else:
        vfm_next[rand_channel] = vfm_prev[rand_channel] + step

    evaluate_volt_diff_all_channels(vfm_next)

    # Repeat for the hfm channels
    hfm_prev = {}

    for index, channel in hfm.channels.items():
        hfm_prev[index] = yield from bps.rd(channel)
    hfm_next = {**hfm_prev}

    rand_channel = get_random_channel(hfm)
    # step = rand.uniform(-20, 20)
    step = rand.uniform(-200, 200)
    hfm_prev[rand_channel] = yield from bps.rd(hfm.channels[rand_channel])
    if abs(hfm_prev[rand_channel] + step) >= 500:
        hfm_next[rand_channel] = hfm_prev[rand_channel] - step
    else:
        hfm_next[rand_channel] = hfm_prev[rand_channel] + step

    evaluate_volt_diff_all_channels(hfm_next)

    yield from bps.mv(vfm, vfm_next)
    yield from bps.mv(hfm, hfm_next)


def next_mixed_channel(vfm: BimorphMirror, hfm: BimorphMirror) -> MsgGenerator:
    """
    stub - randomly moves voltages across a varying number of channels
    """

    vx = get_random_channel(vfm)
    vy = get_random_channel(vfm)
    if vx > vy:
        vy, vx = vx, vy
    hx = get_random_channel(hfm)
    hy = get_random_channel(hfm)
    if hx > hy:
        hy, hx = hx, hy

    vfm_prev = {}
    vfm_next = {}
    # for index, channel in vfm.channels.items():
    #     if index in range(vx, vy):
    #         step = rand.uniform(-20, 20)
    #         vfm_prev[index] = yield from bps.rd(channel)
    #         if abs(vfm_prev[index] + step) >= 500:
    #             vfm_next[index] = vfm_prev[index] - step
    #         else:
    #             vfm_next[index] = vfm_prev[index] + step

    for index, channel in vfm.channels.items():
        if index in range(vx, vy):
            step = rand.uniform(-20, 20)
            vfm_prev[index] = yield from bps.rd(channel)
            if abs(vfm_prev[index] + step) >= 500:
                vfm_next[index] = vfm_prev[index] - step
            else:
                vfm_next[index] = vfm_prev[index] + step

    evaluate_volt_diff_all_channels(vfm_next)

    # Repeat for the hfm channels
    hfm_prev = {}
    hfm_next = {}
    for index, channel in hfm.channels.items():
        if index in range(hx, hy):
            step = rand.uniform(-20, 20)
            hfm_prev[index] = yield from bps.rd(channel)
            if abs(hfm_prev[index] + step) >= 500:
                hfm_next[index] = hfm_prev[index] - step
            else:
                hfm_next[index] = hfm_prev[index] + step

    evaluate_volt_diff_all_channels(hfm_next)

    print("******")
    print("DEBUG")
    print(range(vx, vy))
    print()
    print(range(hx, hy))
    print()
    print(vfm_next)
    print()
    print(hfm_next)
    print("******")

    yield from bps.mv(vfm, vfm_next)
    yield from bps.mv(hfm, hfm_next)


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
        # if rand.uniform(0, 9) <= 5:
        #    for _ in range(data_collection_size):
        #        # 60%
        #        if rand.uniform(0, 9) <= 7:
        #            yield from next_mixed_channel(vfm, hfm)
        #        elif rand.uniform(0, 9) <= 6:
        #            # 20%
        #            yield from next_single_channel(vfm, hfm)
        #        else:
        #            # 20%
        #            yield from next_all_channels(vfm, hfm)
        #        yield from bps.trigger_and_read(devices)  # data out
        # 20%
        if rand.uniform(0, 9) <= 9:  # 7
            for _ in range(data_collection_size):
                # yield from next_all_channels(vfm, hfm)
                yield from next_single_channel(vfm, hfm)
                yield from bps.trigger_and_read(devices)
        # 20%
        # elif rand.uniform(0, 9) <= 9:
        #    for _ in range(data_collection_size):
        #        yield from next_mixed_channel(vfm, hfm)
        #        yield from bps.trigger_and_read(devices)
        ## 20%
        # else:
        #    for _ in range(data_collection_size):
        #        yield from next_single_channel(vfm, hfm)
        #        yield from bps.trigger_and_read(devices)

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
            yield from bps.trigger_and_read(devices)

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
