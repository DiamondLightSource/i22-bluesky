import numpy as np
from bluesky.plan_stubs import mv, read, wait
from bluesky.protocols import Movable
from bluesky.utils import MsgGenerator
from dodal.beamlines.i22 import dcm
from dodal.plans import step_scan  # requires dodal #1734 to do step scans
from ophyd_async.core import AsyncReadable


# Common scan types
def relative_scan(
    motor: Movable,
    start_point: float,
    end_point: float,
    step_size: float,
    readback_device: AsyncReadable,
) -> MsgGenerator:
    """Do a relative scan around a point, with backlash correction, return results"""
    # Prepare the readback device

    # Get motor starting_position
    starting_pos = yield from read(motor)
    # Scan motor from (starting_position+start_point) to (starting_position+end_point)
    # with readback_diode as a detector
    yield from step_scan(
        detectors=[readback_device],
        params={
            motor: [starting_pos + start_point, starting_pos + end_point, step_size]
        },
    )
    # Move to starting_position+start_point for backlash correction
    yield from mv(motor, starting_pos + start_point, group="foo")
    # Do some math with the acquired data?

    # Wait for it to finish moving
    yield from wait(group="foo")
    # Return the results


def knife_edge_scan(
    motor: Movable,
    start_point: float,
    end_point: float,
    step_size: float,
    readback_device: AsyncReadable,
) -> MsgGenerator:
    """Do a relative scan and return the position of the edge"""
    # Do a relative_scan
    yield from relative_scan(
        motor=motor,
        start_point=start_point,
        end_point=end_point,
        step_size=step_size,
        readback_device=readback_device,
    )
    # Return the edge position (one gaussian fit to the 1st derivative peak)


def peak_scan(
    motor: Movable,
    start_point: float,
    end_point: float,
    step_size: float,
    readback_device: AsyncReadable,
) -> MsgGenerator:
    """Do a relative scan and return the position of the peak"""
    # Do a relative_scan
    yield from relative_scan(
        motor=motor,
        start_point=start_point,
        end_point=end_point,
        step_size=step_size,
        readback_device=readback_device,
    )
    # Return the peak position (one gaussian fit to the peak)


def expanding_peak_scan(
    motor: Movable,
    start_point: float,
    end_point: float,
    step_size: float,
    readback_device: AsyncReadable,
    scan_range_factors: list[float] = (1, 2, 5),
) -> MsgGenerator:
    """Do a peak_scan, ensure a peak intensity over a threshold over an expanding range.

    If a peak is not found in the originally requested range, the range is expanded
    incrementally according to scan_range_factors, which default to (1,2,5). Step size
    does not change."""
    peak_present = False
    for scan_range_factor in scan_range_factors:
        if not peak_present:
            yield from relative_scan(
                motor=motor,
                start_point=start_point * scan_range_factor,
                end_point=end_point * scan_range_factor,
                step_size=step_size,
                readback_device=readback_device,
            )
    #       fit a peak
    #       if peak_top > (peak_offset * 1e1): # Top of peak is more than 1 order of
    #                                            magnitude above background
    #           peak_present = True
    # Return the peak position


def channel_scan(
    motor: Movable,
    start_point: float,
    end_point: float,
    step_size: float,
    readback_device: AsyncReadable,
) -> MsgGenerator:
    """Do a relative scan and return the position of the centre"""
    # Do a relative_scan
    yield from relative_scan(
        motor=motor,
        start_point=start_point,
        end_point=end_point,
        step_size=step_size,
        readback_device=readback_device,
    )
    # Return the centre of the edges (two gaussians fit to the 1st derivative peaks)


def max_val_scan(
    motor: Movable,
    start_point: float,
    end_point: float,
    step_size: float,
    readback_device: AsyncReadable,
) -> MsgGenerator:
    """Do a relative scan and return the position maximum value"""
    # Do a relative_scan
    yield from relative_scan(
        motor=motor,
        start_point=start_point,
        end_point=end_point,
        step_size=step_size,
        readback_device=readback_device,
    )
    # Return the position of the maximum value


# Shared Alignment Routines
def parallel_condition_refiner(
    yaw_motor: Movable,
    x_motor: Movable,
    readback_device: AsyncReadable,
    yaw_value: float,
) -> MsgGenerator:
    """Iteratively refine position of crystal to ensure it is parallel to beam"""

    number_of_iterations = 0
    on_peak = False
    while not on_peak:
        # Get starting position of yaw motor
        yaw_starting_pos = yield from read(yaw_motor)
        # Do a max_val_scan of the yaw motor (-num to +num, in steps of num (3 points))
        yaw_pos = yield from max_val_scan(
            motor=yaw_motor,
            start_point=-yaw_value,
            end_point=yaw_value,
            step_size=yaw_value,
        )
        # Move to position (blocking)
        yield from mv(yaw_motor, yaw_pos, group="foo")
        yield from wait(group="foo")
        # Do a knife_edge_scan of x (+/- 0.5 mm, step 0.05 mm)
        x_pos = yield from knife_edge_scan(
            motor=x_motor,
            start_point=-0.5,
            end_point=0.5,
            step_size=0.05,
            readback_device=readback_device,
        )
        # Move to position (non-blocking)
        yield from mv(x_motor, x_pos, group="bar")
        # Check if you're done refining
        if np.floor(yaw_pos) == np.floor(yaw_starting_pos):
            on_peak = True
        if number_of_iterations > 10:
            raise
        number_of_iterations += 1
        # Wait for move to complete
        yield from wait(group="bar")


def align_crystal(
    yaw_motor: Movable,
    x_motor: Movable,
    readback_device: AsyncReadable,
    readback_motor: Movable,
) -> MsgGenerator:
    """Do a relative scan and return the position of the edge (1st derivative peak)"""
    # Do a wide channel_scan of channel (+/- 5 mm, step 0.1 mm)
    x_pos = yield from channel_scan(
        motor=x_motor,
        start_point=-5,
        end_point=5,
        step_size=0.1,
        readback_device=readback_device,
    )
    # Move to position (blocking)
    yield from mv(x_motor, x_pos, group="foo")
    yield from wait(group="foo")
    # Do a wide channel_scan of yaw (+/- 6 deg, step 0.3 deg)
    yaw_pos = yield from channel_scan(
        motor=yaw_motor,
        start_point=-6,
        end_point=6,
        step_size=0.3,
        readback_device=readback_device,
    )
    # Move to position (blocking)
    yield from mv(yaw_motor, yaw_pos, group="bar")
    yield from wait(group="bar")
    # Do a knife_edge_scan of rotation face (relative scan 0 mm to 2.5 mm, step 0.05 mm)
    x_pos = yield from knife_edge_scan(
        motor=x_motor,
        start_point=0,
        end_point=0.25,
        step_size=0.05,
        readback_device=readback_device,
    )
    # Move to position (blocking)
    yield from mv(x_motor, x_pos, group="foo")
    yield from wait(group="foo")
    # Do a parallel_condition_refiner with yaw_value = 5 deg
    yield from parallel_condition_refiner(
        yaw_motor=yaw_motor,
        x_motor=x_motor,
        readback_device=readback_device,
        yaw_value=5,
    )
    # Do a parallel_condition_refiner with yaw_value = 1 deg
    yield from parallel_condition_refiner(
        yaw_motor=yaw_motor,
        x_motor=x_motor,
        readback_device=readback_device,
        yaw_value=1,
    )
    # Do a max_val_scan of the yaw motor (+/- 1.2 deg, step 0.03 deg)
    yaw_pos = max_val_scan(
        motor=yaw_motor,
        start_point=-1.2,
        end_point=1.2,
        step_size=0.03,
        readback_device=readback_device,
    )
    # Move to position (blocking)
    yield from mv(x_motor, x_pos, group="foo")
    yield from wait(group="foo")
    # Do a knife_edge_scan of the x motor (+/- 0.5 mm, step 0.01 mm)
    x_pos = yield from knife_edge_scan(
        motor=x_motor,
        start_point=-0.5,
        end_point=0.5,
        step_size=0.01,
        readback_device=readback_device,
    )
    # Move to position (blocking)
    yield from mv(x_motor, x_pos, group="foo")
    yield from wait(group="foo")
    # Get starting position of diode_x, add 12.39 mm and move it there
    readback_motor_pos = yield from read(readback_motor)
    yield from mv(readback_motor, readback_motor_pos + 12.39)
    # Get the energy you're at
    energy = yield from read(dcm)
    h = 6.6261e-34
    c = 2.9979e8
    si_d_spacing = 1.920155716e-10  # https://physics.nist.gov/cgi-bin/cuu/Value?d220sil
    conversion_factor = 6.2415064799632e15
    energy_in_joules = energy / conversion_factor
    bragg_angle = 0.5 * np.degrees(np.asin((h * c) / (si_d_spacing * energy_in_joules)))
    # Get starting position of yaw, add bragg_angle for energy and move it there
    yaw_pos = yield from read(yaw_motor)
    yield from mv(yaw_motor, yaw_pos + bragg_angle, group="foo")
    yield from wait(group="foo")


def balance_yaw_motors() -> None:
    """If balance coarse yaw and fine yaw so fine yaw == 0"""

    # Get position of fine yaw and coarse yaw
    # If fine yaw is too far away from 0, move coarse yaw and fine yaw
    # Do a peak_scan of fine yaw motor to recenter on Bragg condition
    ...


# Unique Alignment Routines
def align_upstream() -> None:
    """Align the upstream crystal and USAXS diode"""

    # Do the shared align_crystal routine
    # Do a coarse peak_scan of the Bragg condition on the coarse yaw motor (+/- 0.4 deg,
    # step 0.003 deg)
    # Move to position
    # Do a fine peak_scan of the Bragg condition on the coarse yaw motor (+/- 0.06 deg,
    # step 0.0006 deg)
    # Move to position
    # Do a peak_scan of the diode x motor (+/- 15 mm, step 0.5 mm)
    # Move to position
    # Do a peak_scan of the fine yaw motor (+/- 1000 um, step 10 um)
    # Move to position
    # Prompt user to put US pinhole in???
    ...


def align_downstream() -> None:
    """Align the downstream crystal and USAXS diode"""

    # Do the shared align_crystal routine
    # Change tetramm gain to high (1)
    # Do a coarse max_val of the Bragg condition on the coarse yaw motor (+/- 0.4 deg,
    # step 0.003 deg)
    # Move to position
    # Do a peak_scan of the diode x motor (+/- 15 mm, step 0.5 mm)
    # Move to position
    # Change tetramm gain to low (0)
    # Do a coarse peak_scan of the Bragg condition on the fine yaw motor (+/- 1000 um,
    # step 10 um)
    # Move to position
    # Do a fine peak_scan of the fine yaw motor (+/- 100 um, step 1 um)
    # Move to position
    ...


def realign_upstream() -> None:
    """Re-align the upstream crystal"""

    # Move everything to the correct positions
    # Do an expanding_peak_scan of the upstream crystal
    # Move to position
    # Balance yaw motors???
    ...


def realign_downstream() -> None:
    """Re-align the downstream crystal"""

    # Move everything to the correct positions
    # Do an expanding_peak_scan of the downstream crystal
    # Move to position
    # Balance yaw motors???
    ...


def save_alignment_positions() -> None:
    """Save alignment positions for all scan types

    Scan Type:      Downstream  Upstream    SWAXS
    Motor:          Motor Positions:
    bs2_x:          DS          US          DS
    bs2_y:          DS/US       DS/US       DS/US
    usaxs_ux:       DS/US       DS/US       DS/US
    usaxs uyaw:     DS/US       DS/US       DS/US
    usaxs ufyaw:    DS/US       DS/US       DS/US
    usaxs dx:       DS          US          US
    usaxs dyaw:     DS/US       DS/US       DS/US
    usaxs dfyaw:    DS/US       DS/US       DS/US
    """
    # Where should these be saved?
    ...
