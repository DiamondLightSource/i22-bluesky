[![CI](https://github.com/DiamondLightSource/i22-bluesky/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/i22-bluesky/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/i22-bluesky/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/i22-bluesky)
[![PyPI](https://img.shields.io/pypi/v/i22-bluesky.svg)](https://pypi.org/project/i22-bluesky)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# i22_bluesky

Plans and behaviours specific to the i22 beamline at DiamondLightSource.

This module is intended to hold plans, stubs and other behaviours that are
unique to the operation of the i22 beamline at Diamond Light Source, and to
act as a repository in which development of said plans, stubs and behaviours
may occur.

The 'plans' package contains functions that describe a full operation which performs an experiment and captures data.
The 'stubs' package contains modular partial instructions that may act as a building block for constructing plans.

Source          | <https://github.com/DiamondLightSource/i22-bluesky>
:---:           | :---:
PyPI            | `pip install i22-bluesky`
Releases        | <https://github.com/DiamondLightSource/i22-bluesky/releases>

This repository is also intended to act as a planFunctions configuration source
for the i22 instance of BlueAPI.

.. code-block:: yaml

    env:
      sources:
        - kind: planFunctions
          module: i22-bluesky.plans

