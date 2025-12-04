# Common scan types
def relative_scan() -> None: ...


"""Do a relative scan around a point, with backlash correction, return results
Get starting position of motor
Do relative scan around that position
Move back to starting position
Fit and return results
"""


def knife_edge_scan() -> None: ...


"""Do a relative scan and return the position of the edge
(1st derivative peak)
"""


def peak_scan() -> None: ...


"""Do a relative scan and return the position of the peak
(peak fit to data)
"""


def channel_scan() -> None: ...


"""Do a relative scan and return the position of the centre
(centre of 1st derivative peaks)
"""


def max_val_scan() -> None: ...


"""Do a relative scan and return the position maximum value
"""


# Shared Alignment Routines
def parallel_condition_refiner() -> None: ...


"""Iteratively refine position of crystal to ensure it is || to beam
"""

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
#   inrement number_of_iterations


def align_crystal() -> None: ...


"""Do a relative scan and return the position of the edge (1st derivative peak)
"""

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
# Get starting position of yaw, add bragg_angle for energy and move it there


# Unique Alignment Routines
def align_upstream() -> None: ...


def align_downstream() -> None: ...


def realign_upstream() -> None: ...


def realign_downstream() -> None: ...


def save_alignment_positions() -> None: ...
