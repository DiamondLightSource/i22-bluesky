from collections.abc import Callable

import numpy as np
from bluesky.utils import MsgGenerator

from i22_bluesky.plans.pressure_jump import pressure_jump


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
