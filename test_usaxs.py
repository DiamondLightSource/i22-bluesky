"""
In ophyd-async>src>ophyd_async>sim>_pattern_generator.py>generate_interesting_pattern
replace line 34 with:
    A = channel * 100
    x0 = 0
    sigma = 1
    v0 = offset
    return A * np.exp(-((x - x0) ** 2) / (2 * sigma**2)) + v0
In ophyd-async>src>ophyd_async>sim>_point_detector.py>SimPointDetector
replace line 83 with:
    setter(int(point))
"""

import bluesky.plan_stubs as bps  # noqa: F401
import bluesky.plans as bp  # noqa: F401
import bluesky.preprocessors as bpp  # noqa: F401
from bluesky.callbacks import PeakStats
from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.run_engine import RunEngine
from ophyd_async import sim
from ophyd_async.core import init_devices

from i22_bluesky.usaxs.alignment import peak_scan

# Create a run engine and make ipython use it for `await` commands
RE = RunEngine(call_returns_result=True)

# Add a callback for plotting
bec = BestEffortCallback()
RE.subscribe(bec)

# Make a pattern generator that uses the motor positions
# to make a test pattern. This simulates the real life process
# of X-ray scattering off a sample
pattern_generator = sim.PatternGenerator()


# All Devices created within this block will be
# connected and named at the end of the with block
with init_devices():
    # Create a sample stage with X and Y motors that report their positions
    # to the pattern generator
    stage = sim.SimStage(pattern_generator)
    # Make a detector device that gives the point value of the pattern generator
    # when triggered
    pdet = sim.SimPointDetector(pattern_generator)

result = RE(bps.rd(stage.x))
print(f"Initial position of motor is: {result.plan_result}")

RE(bps.abs_set(stage.x.velocity, 10))

pp = PeakStats(stage.x, pdet)

result = RE(peak_scan(stage.x, -1, 1, 0.5, pdet, "pdet-channel-1-value"), pp)
# result = RE(absolute_scan(stage.x, -1, 1, 0.5, pdet, "pdet-channel-1-value"))

print(f"PeakStatsResults: {pp.max}")

result = RE(bps.rd(stage.x))
print(f"Final position of motor is: {result.plan_result}")
