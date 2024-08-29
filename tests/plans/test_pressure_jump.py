from pathlib import Path
from typing import Any, Callable

import bluesky.plan_stubs as bps
import bluesky.plans as bp
import bluesky.preprocessors as bpp
import numpy as np
from bluesky.protocols import Readable
from dodal.common import MsgGenerator, inject
from dodal.devices.tetramm import TetrammDetector
from dodal.plans.data_session_metadata import attach_data_session_metadata_decorator
from ophyd_async.core import HardwareTriggeredFlyable
from ophyd_async.core.detector import DetectorTrigger, StandardDetector, TriggerInfo
from ophyd_async.core.device_save_loader import load_device
from ophyd_async.core.utils import in_micros
from ophyd_async.panda import HDFPanda, StaticSeqTableTriggerLogic
from ophyd_async.panda._table import (
    SeqTable,
    SeqTableRow,
    SeqTrigger,
    seq_table_from_rows,
)
from ophyd_async.panda._trigger import SeqTableInfo
from ophyd_async.plan_stubs import (
    fly_and_collect,
)

from i22_bluesky.plans.stopflow import (
    DEADTIME_BUFFER,
    DEFAULT_BASELINE_MEASUREMENTS,
    raise_for_minimum_exposure_times,
)


def explore_function_output_space(
    func: Callable[[float, float, float]], **fixed_params
):
    def wrapped_func(a, b, c):
        return func(a, b, c, **fixed_params)

    # Define the ranges for a, b, c using linspace
    a_values = np.linspace(
        150, 250, num=100
    )  # 100 steps from 150 to 250 - start pressure
    b_values = np.linspace(
        1500, 3000, num=100
    )  # 100 steps from 1500 to 3000 - end pressure
    c_values = np.linspace(
        5, 600, num=100
    )  # 100 steps from 5 to 600 - duration in seconds

    results = []

    # Iterate over all combinations of a, b, c
    for a in a_values:
        for b in b_values:
            for c in c_values:
                # Calculate the function output and store the result
                result = wrapped_func(a, b, c)
                results.append((a, b, c, result))

    return results


# Example usage
def example_function(a, b, c):
    return a + b * c


output = explore_function_output_space(example_function, num_frames=1, exposure=0.1)


def test_pressure_jump_space() -> MsgGenerator:
    explore_function_output_space(pressure_jump, exposure=0.5)
