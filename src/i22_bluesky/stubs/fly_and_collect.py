from __future__ import annotations

import bluesky.plan_stubs as bps
from bluesky.utils import short_uid
from ophyd_async.core import (
    StandardDetector,
    StandardFlyer,
)
from ophyd_async.fastcs.panda import SeqTableInfo


def fly_and_collect(
    stream_name: str,
    flyer: StandardFlyer[SeqTableInfo],
    detectors: list[StandardDetector],
):
    """Kickoff, complete and collect with a flyer and multiple detectors.

    This stub takes a flyer and one or more detectors that have been prepared. It
    declares a stream for the detectors, then kicks off the detectors and the flyer.
    The detectors are collected until the flyer and detectors have completed.

    """
    yield from bps.declare_stream(*detectors, name=stream_name, collect=True)
    yield from bps.kickoff(flyer, wait=True)
    for detector in detectors:
        yield from bps.kickoff(detector)

    # collect_while_completing
    group = short_uid(label="complete")

    yield from bps.complete(flyer, wait=False, group=group)
    for detector in detectors:
        yield from bps.complete(detector, wait=False, group=group)

    done = False
    while not done:
        try:
            yield from bps.wait(group=group, timeout=0.5)
        except TimeoutError:
            pass
        else:
            done = True
        yield from bps.collect(
            *detectors,
            return_payload=False,
            name=stream_name,
        )
    yield from bps.wait(group=group)
