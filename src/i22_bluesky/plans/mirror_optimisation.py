import random as rand
import time

import bluesky.preprocessors as bpp
from bluesky import plan_stubs as bps
from bluesky.utils import MsgGenerator
from dodal.devices.bimorph_mirror import BimorphMirror, BimorphMirrorStatus
from dodal.beamlines.i22 import BeamDevice
from dodal.plan_stubs.data_session import attach_data_session_metadata_decorator
from ophyd_async.core import SignalR, StandardDetector
from ophyd_async.core import (
    SignalR,
    wait_for_value,
)
# 3000 iterations of the Adam algorithm per fold

data_collection_size = 15
rand_range = (-200, 200)
DEFAULT_TIMEOUT = 60


def get_random_channel(mirror: BimorphMirror) -> int:
    return rand.choice(list(mirror.channels))


def evaluate_volt_diff_all_channels(old_mirror: dict[int, float], mirror: dict[int, float], mirror_name: str) -> None:
    for index in mirror:
        if index + 1 in mirror:
            channel_diff = mirror[index] - mirror[index + 1]
            old_diff = mirror[index] - old_mirror[index + 1]
            if abs(channel_diff) >= 500 or abs(old_diff) >= 500:
                print(f"Voltage protection: {mirror[index]} - {mirror[index + 1]} = {channel_diff} for {mirror_name}")
                mirror[index + 1] = 0


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
        step = int(rand.uniform(*rand_range))
        vfm_prev[index] = yield from bps.rd(channel)
        if abs(vfm_prev[index] + step) >= 500:
            vfm_next[index] = vfm_prev[index] - step
        else:
            vfm_next[index] = vfm_prev[index] + step

    evaluate_volt_diff_all_channels(vfm_prev, vfm_next, "vfm")

    # Repeat for the hfm channels
    hfm_prev = {}
    hfm_next = {}
    for index, channel in hfm.channels.items():
        step = int(rand.uniform(*rand_range))
        hfm_prev[index] = yield from bps.rd(channel)
        if abs(hfm_prev[index] + step) >= 500:
            hfm_next[index] = hfm_prev[index] - step
        else:
            hfm_next[index] = hfm_prev[index] + step

    evaluate_volt_diff_all_channels(hfm_prev, hfm_next, "hfm")

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
    step = int(rand.uniform(*rand_range))
    vfm_prev[rand_channel] = yield from bps.rd(vfm.channels[rand_channel])
    if abs(vfm_prev[rand_channel] + step) >= 500:
        vfm_next[rand_channel] = vfm_prev[rand_channel] - step
    else:
        vfm_next[rand_channel] = vfm_prev[rand_channel] + step

    evaluate_volt_diff_all_channels(vfm_prev, vfm_next, "vfm")

    # Repeat for the hfm channels
    hfm_prev = {}

    for index, channel in hfm.channels.items():
        hfm_prev[index] = yield from bps.rd(channel)
    hfm_next = {**hfm_prev}

    rand_channel = get_random_channel(hfm)
    step = int(rand.uniform(*rand_range))
    hfm_prev[rand_channel] = yield from bps.rd(hfm.channels[rand_channel])
    if abs(hfm_prev[rand_channel] + step) >= 500:
        hfm_next[rand_channel] = hfm_prev[rand_channel] - step
    else:
        hfm_next[rand_channel] = hfm_prev[rand_channel] + step

    evaluate_volt_diff_all_channels(hfm_prev, hfm_next, "hfm")

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
    for index, channel in vfm.channels.items():
        if index in range(vx, vy):
            step = int(rand.uniform(*rand_range))
            vfm_prev[index] = yield from bps.rd(channel)
            if abs(vfm_prev[index] + step) >= 500:
                vfm_next[index] = vfm_prev[index] - step
            else:
                vfm_next[index] = vfm_prev[index] + step

    evaluate_volt_diff_all_channels(vfm_prev, vfm_next, "vfm")

    # Repeat for the hfm channels
    hfm_prev = {}
    hfm_next = {}
    for index, channel in hfm.channels.items():
        if index in range(hx, hy):
            step = int(rand.uniform(*rand_range))
            hfm_prev[index] = yield from bps.rd(channel)
            if abs(hfm_prev[index] + step) >= 500:
                hfm_next[index] = hfm_prev[index] - step
            else:
                hfm_next[index] = hfm_prev[index] + step

    evaluate_volt_diff_all_channels(hfm_prev, hfm_next, "hfm")

    yield from bps.mv(vfm, vfm_next)
    yield from bps.mv(hfm, hfm_next)


def good_mirror_config(vfm: BimorphMirror, hfm: BimorphMirror) -> MsgGenerator:
    """
    stub - return bimorph mirror to known configuration
    """

    yield from bps.abs_set(vfm.target_apply, "VFMSS", wait=True)
    yield from bps.wait_for([lambda: wait_for_value(vfm.status, BimorphMirrorStatus.BUSY, timeout=DEFAULT_TIMEOUT)])     
    yield from bps.wait_for([lambda: wait_for_value(vfm.status, BimorphMirrorStatus.IDLE, timeout=DEFAULT_TIMEOUT)])     
    yield from bps.abs_set(hfm.target_apply, "HFMSS", wait=True)
    yield from bps.wait_for([lambda: wait_for_value(hfm.status, BimorphMirrorStatus.BUSY, timeout=DEFAULT_TIMEOUT)])     
    yield from bps.wait_for([lambda: wait_for_value(hfm.status, BimorphMirrorStatus.IDLE, timeout=DEFAULT_TIMEOUT)])     



def ensure_beam_readiness(beam_device: BeamDevice) -> MsgGenerator:
    top_up_countdown: SignalR[float] = beam_device.topup_countdown  # type: ignore
    beam_intensity: SignalR[float] = beam_device.beam_intensity  # type: ignore
    time_until_top_up: int = yield from bps.rd(top_up_countdown)
    while (time_until_top_up >= 580 or time_until_top_up <= 15):
        next_sleep = time_until_top_up - 580 + 1 if time_until_top_up >= 580 else 15
        yield from bps.sleep(next_sleep)
        time_until_top_up = yield from bps.rd(top_up_countdown)
    current_beam_intensity: float = yield from bps.rd(beam_intensity)
    while current_beam_intensity < 1e-5:
        yield from bps.sleep(15)
        current_beam_intensity = yield from bps.rd(beam_intensity)



@attach_data_session_metadata_decorator()
def random_bimorph_mirror_data_collection(
    vfm: BimorphMirror,
    hfm: BimorphMirror,
    detectors: set[StandardDetector],
    beam_device: BeamDevice,
    
) -> MsgGenerator:
    """
    plan - move the vertical and horizonal bimorph mirrors by random amounts

    Will randomly create datasets with the following:
    - Just single channel movements
    - Move all channels at once
    - Move all channels sometimes, otherwise alter single channels

    """
    devices = [vfm, hfm, *detectors, beam_device]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md={"detectors": ["ss"]})
    def innerplan():
        yield from good_mirror_config(vfm, hfm)
        num = int(rand.uniform(0, 9))
        # Do split 40% of the time
        if num <= 3:
            for _ in range(data_collection_size):
                num = int(rand.uniform(0, 9))
                if num <= 5:
                    # 60%
                    yield from next_mixed_channel(vfm, hfm)
                elif num == 6 or 7:
                    # 20%
                    yield from next_single_channel(vfm, hfm)
                else:
                    # 20%
                    yield from next_all_channels(vfm, hfm)
                yield from ensure_beam_readiness(beam_device)
                yield from bps.trigger_and_read(devices)
        # 20%
        elif num == 4 or 5:
            for _ in range(data_collection_size):
                yield from next_single_channel(vfm, hfm)
                yield from ensure_beam_readiness(beam_device)
                yield from bps.trigger_and_read(devices)
        # 20%
        elif num == 6 or 7:
            for _ in range(data_collection_size):
                yield from next_mixed_channel(vfm, hfm)
                yield from ensure_beam_readiness(beam_device)
                yield from bps.trigger_and_read(devices)
        # 20%
        else:
            for _ in range(data_collection_size):
                yield from next_single_channel(vfm, hfm)
                yield from ensure_beam_readiness(beam_device)
                yield from bps.trigger_and_read(devices)

    yield from innerplan()
    yield from good_mirror_config(vfm, hfm)


@attach_data_session_metadata_decorator()
def testing_bimorph_mirror_data_collection(
    vfm: BimorphMirror,
    hfm: BimorphMirror,
    detectors: set[StandardDetector],
    beam_device: BeamDevice
) -> MsgGenerator:
    """
    plan - move the vertical and horizonal bimorph mirrors according to
    a chosen stub.

    Used to test stubs.
    """
    devices = [vfm, hfm, *detectors, beam_device]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md={"detectors": ["ss"]})
    def innerplan():
        yield from good_mirror_config(vfm, hfm)
        for _ in range(data_collection_size):
            yield from next_single_channel(vfm, hfm)
            yield from ensure_beam_readiness(beam_device)
            yield from bps.trigger_and_read(devices)

    yield from innerplan()
    yield from good_mirror_config(vfm, hfm)


# @attach_data_session_metadata_decorator()
# def bimorph_cleanup(
#     mirror: BimorphMirror, detectors: set[StandardDetector]
# ) -> MsgGenerator:
#     """
#     plan - return to known mirror configuration
#     """
#     devices = [mirror, *detectors]

#     @bpp.stage_decorator(devices)
#     @bpp.run_decorator(md={"detectors": ["ss"]})
#     def innerplan():
#         for _ in range(data_collection_size):
#             yield from good_mirror_config(mirror)
#             yield from ensure_beam_readiness(beam_device)
#             yield from bps.trigger_and_read(devices)

#     yield from innerplan()


def voltage_held_over_time(
    vfm: BimorphMirror,
    hfm: BimorphMirror,
    detectors: set[StandardDetector],
    beam_device: BeamDevice, 
    settle_time: float = 50,
) -> MsgGenerator:
    devices = [vfm, hfm, *detectors, beam_device]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md={"detectors": ["ss"]})
    def innerplan():
        yield from good_mirror_config(vfm, hfm)
        num = int(rand.uniform(0, 9))
        # Do split 40% of the time
        if num <= 3:
            for _ in range(data_collection_size):
                num = int(rand.uniform(0, 9))
                if num <= 5:
                    # 60%
                    yield from next_mixed_channel(vfm, hfm)
                elif num == 6 or 7:
                    # 20%
                    yield from next_single_channel(vfm, hfm)
                else:
                    # 20%
                    yield from next_all_channels(vfm, hfm)
                yield from ensure_beam_readiness(beam_device)
                yield from bps.trigger_and_read(devices)
                yield from bps.sleep(settle_time)
        # 20%
        elif num == 4 or 5:
            for _ in range(data_collection_size):
                yield from next_single_channel(vfm, hfm)
                yield from ensure_beam_readiness(beam_device)
                yield from bps.trigger_and_read(devices)
                yield from bps.sleep(settle_time)
        # 20%
        elif num == 6 or 7:
            for _ in range(data_collection_size):
                yield from next_mixed_channel(vfm, hfm)
                yield from ensure_beam_readiness(beam_device)
                yield from bps.trigger_and_read(devices)
                yield from bps.sleep(settle_time)
        # 20%
        else:
            for _ in range(data_collection_size):
                yield from next_single_channel(vfm, hfm)
                yield from ensure_beam_readiness(beam_device)
                yield from bps.trigger_and_read(devices)
                yield from bps.sleep(settle_time)

    while time.time() < 1737017640:
        yield from innerplan()
        yield from good_mirror_config(vfm, hfm)


#########################################################
# New
#########################################################


@attach_data_session_metadata_decorator()
def mixed_bimorph_mirror_data_collection(
    mirror: BimorphMirror,
    vfm: BimorphMirror,
    hfm: BimorphMirror,
    detectors: set[StandardDetector],
    beam_device: BeamDevice
) -> MsgGenerator:
    """
    Adjust a varying number of bimorph mirror channels for each
    round of data collection.
    """
    devices = [vfm, hfm, *detectors, beam_device]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md={"detectors": ["ss"]})
    def innerplan():
        yield from good_mirror_config(vfm, hfm)
        for _ in range(data_collection_size):
            num = int(rand.uniform(0, 9))
            if num <= 5:
                # 60%
                yield from next_mixed_channel(vfm, hfm)
            elif num == 6 or 7:
                # 20%
                yield from next_single_channel(vfm, hfm)
            else:
                # 20%
                yield from next_all_channels(vfm, hfm)
            yield from ensure_beam_readiness(beam_device)
            yield from bps.trigger_and_read(devices)

    yield from innerplan()
    yield from good_mirror_config(vfm, hfm)


@attach_data_session_metadata_decorator()
def single_bimorph_mirror_data_collection(
    vfm: BimorphMirror, hfm: BimorphMirror, detectors: set[StandardDetector],
    beam_device: BeamDevice, 
) -> MsgGenerator:
    """
    Adjust a single bimorph mirror channel for each round
    of data collection.
    """
    devices = [vfm, hfm, *detectors, beam_device]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md={"detectors": ["ss"]})
    def innerplan():
        yield from good_mirror_config(vfm, hfm)
        for _ in range(data_collection_size):
            yield from next_single_channel(vfm, hfm)
            yield from ensure_beam_readiness(beam_device)
            yield from bps.trigger_and_read(devices)

    yield from innerplan()
    yield from good_mirror_config(vfm, hfm)


@attach_data_session_metadata_decorator()
def all_bimorph_mirror_data_collection(
    vfm: BimorphMirror,
    hfm: BimorphMirror,
    detectors: set[StandardDetector],
    beam_device: BeamDevice,
    
) -> MsgGenerator:
    """
    Adjust all bimorph mirror channels for each round
    of data collection.
    """
    devices = [vfm, hfm, *detectors, beam_device]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md={"detectors": ["ss"]})
    def innerplan():
        yield from good_mirror_config(vfm, hfm)
        for _ in range(data_collection_size):
            yield from next_all_channels(vfm, hfm)
            yield from ensure_beam_readiness(beam_device)
            yield from bps.trigger_and_read(devices)

    yield from innerplan()
    yield from good_mirror_config(vfm, hfm)


@attach_data_session_metadata_decorator()
def varied_bimorph_mirror_data_collection(
    vfm: BimorphMirror,
    hfm: BimorphMirror,
    detectors: set[StandardDetector],
    beam_device: BeamDevice,
    
) -> MsgGenerator:
    """
    Adjust a random number of bimorph mirror channels
    for each round of data collection.
    """
    devices = [vfm, hfm, *detectors, beam_device]

    @bpp.stage_decorator(devices)
    @bpp.run_decorator(md={"detectors": ["ss"]})
    def innerplan():
        yield from good_mirror_config(vfm, hfm)
        for _ in range(data_collection_size):
            yield from next_mixed_channel(vfm, hfm)
            yield from ensure_beam_readiness(beam_device)
            yield from bps.trigger_and_read(devices)

    yield from innerplan()
    yield from good_mirror_config(vfm, hfm)



def multi_capture(
    vfm: BimorphMirror,
    hfm: BimorphMirror,
    detectors: set[StandardDetector],
    beam_device: BeamDevice,
) -> MsgGenerator:
    while time.time() < 1737449400:
        try:
            num = int(rand.uniform(0, 9))
            if num <= 5:
                # 60%
                print("all_bimorph_mirror_data_collection")
                yield from all_bimorph_mirror_data_collection(vfm, hfm, detectors, beam_device)
            elif num in {6, 7, 8}:
                # 30%
                print("varied_bimorph_mirror_data_collection")
                yield from varied_bimorph_mirror_data_collection(vfm, hfm, detectors, beam_device)
            else:
                # 10%
                print("single_bimorph_mirror_data_collection")
                yield from single_bimorph_mirror_data_collection(vfm, hfm, detectors, beam_device)
        except:
            pass
            


#########################################################
# Template
#########################################################


@attach_data_session_metadata_decorator()
def mirror_output(
    mirror: BimorphMirror,
    beam_device: BeamDevice,
    
) -> MsgGenerator:
    """
    plan - print the dict of all channel voltages
    """

    @bpp.stage_decorator([mirror, beam_device])
    @bpp.run_decorator(md={"detectors": ["ss"]})
    def innerplan():
        yield from ensure_beam_readiness(beam_device)
        yield from bps.trigger_and_read([mirror])

    yield from innerplan()



#####################################
    
{
  "name": "all_bimorph_mirror_data_collection",
  "params": {
    "detectors": [
      "ss"
    ],
  "vfm": "bimorph_vfm",
  "hfm": "bimorph_hfm",
  "beam_device": "beam_device"
  }
}



# bluesky.utils.FailedStatus: <AsyncStatus, device: bimorph_hfm, task: <coroutine object BimorphMirror.set at 0x7f3976773a40>,
# errored: TimeoutError("bimorph_hfm-channels-10-output_voltage didn't match -395.0 in 25s, last value -438.0")>

# bluesky.utils.FailedStatus: <AsyncStatus, device: bimorph_vfm, task: <coroutine object BimorphMirror.set at 0x7fa33b91cd40>,
# errored: TimeoutError("bimorph_vfm-channels-2-output_voltage didn't match 385.0 in 60s, last value 500.0")>