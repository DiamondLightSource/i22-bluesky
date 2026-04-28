from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.plans import adaptive_scan
from bluesky.run_engine import RunEngine
from ophyd_async import sim
from ophyd_async.core import init_devices

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

RE(
    adaptive_scan(
        [pdet],
        "pdet-channel-1-value",
        stage.x,
        start=-10,
        stop=10,
        min_step=0.2,
        max_step=5,
        target_delta=10,
        backstep=True,
        threshold=0.5,
    )
)
