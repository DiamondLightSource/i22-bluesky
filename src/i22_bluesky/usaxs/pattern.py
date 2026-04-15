## pattern generators for the point sim detector


import numpy as np
from ophyd_async import sim


class GaussianPatternGenerator(sim.PatternGenerator):
    def __init__(self):
        super().__init__()

    def generate_point(self, channel=1, high_energy=False) -> float:
        return channel * np.exp(-((0 - self.x) ** 2) / (2 * 0.5**2)) + 0
