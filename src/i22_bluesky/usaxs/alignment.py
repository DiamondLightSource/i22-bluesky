# Common scan types


def relative_scan() -> None:
    """Do a relative scan around a point, with backlash correction, return results
    Get starting position of motor
    Do relative scan around that position
    Move back to starting position
    Fit and return results
    """
    ...


def knife_edge_scan(motor, start_point, end_point, step_size, readbackDevice) -> None:
    """Do a relative scan and return the position of the edge
    (1st derivative peak)
    """

    # Prepare the readback device
    ...


def peak_scan() -> None:
    """Do a relative scan and return the position of the peak
    (peak fit to data)
    """
    ...


def expanding_peak_scan() -> None:
    """Do a peak_scan, ensure a peak intensity over a threshold or expand range"""
    ...


def channel_scan() -> None:
    """Do a relative scan and return the position of the centre
    (centre of 1st derivative peaks)
    """
    ...


def max_val_scan() -> None:
    """Do a relative scan and return the position maximum value"""
    ...


# Shared Alignment Routines
def parallel_condition_refiner() -> None:
    """Iteratively refine position of crystal to ensure it is || to beam"""

    # number_of_iterations = 0
    # on_peak = False
    # while not on_peak:
    #   Get starting position of yaw motor
    #   Do a max_val_scan of the yaw motor (-num to +num, in steps of num (3 points))
    #   Move to position
    #   Do a knife_edge_scan of x (+/- 0.5 mm, step 0.05 mm)
    #   Move to position
    #   if floor(yawPosition) == floor(startingPosition)):
    #       on_peak = True
    #   if number_of_iterations > 10:
    #       stop refining - you didn't find it
    #   increment number_of_iterations
    ...


def align_crystal() -> None:
    """Do a relative scan and return the position of the edge (1st derivative peak)"""

    # Do a wide channel_scan of channel (+/- 5 mm, step 0.1 mm)
    # Move to position
    # Do a wide channel_scan of yaw (+/- 6 deg, step 0.3 deg)
    # Move to position
    # Do a knife_edge_scan of rotation face (relative scan 0 mm to 2.5 mm, step 0.05 mm)
    # Move to position
    # Do a parallel_condition_refiner with yaw_value = 5 deg
    # Do a parallel_condition_refiner with yaw_value = 1 deg
    # Do a max_val_scan of the yaw motor (+/- 1.2 deg, step 0.03 deg)
    # Move to position
    # Do a knife_edge_scan of the x motor (+/- 0.5 mm, step 0.01 mm)
    # Move to position
    # Get starting position of diode_x, add 12.39 mm and move it there
    # Get the energy you're at
    # braggAngle = 0.5 * (180 / 3.14159) * asin((6.6261e-34 * 2.9979e8) /
    # (1.920155716e-10 * (energyPosition / 6.2415064799632e15)))
    # Get starting position of yaw, add bragg_angle for energy and move it there
    ...


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
    ...
