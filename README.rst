i22-bluesky
===========================

|code_ci| |docs_ci| |coverage| |pypi_version| |license|

This module is intended to hold plans, stubs and other behaviours that are
unique to the operation of the i22 beamline at Diamond Light Source, and to
act as a repository in which development of said plans, stubs and behaviours
may occur.

============== ==============================================================
PyPI           ``pip install i22-bluesky``
Source code    https://github.com/DiamondLightSource/i22-bluesky
Documentation  https://DiamondLightSource.github.io/i22-bluesky
Releases       https://github.com/DiamondLightSource/i22-bluesky/releases
============== ==============================================================

This repository is also intended to act as a planFunctions configuration source
for the i22 instance of BlueAPI.

.. code-block:: yaml

env:
  sources:
    - kind: planFunctions
      module: i22-bluesky.plans

.. |code_ci| image:: https://github.com/DiamondLightSource/i22-bluesky/actions/workflows/code.yml/badge.svg?branch=main
    :target: https://github.com/DiamondLightSource/i22-bluesky/actions/workflows/code.yml
    :alt: Code CI

.. |docs_ci| image:: https://github.com/DiamondLightSource/i22-bluesky/actions/workflows/docs.yml/badge.svg?branch=main
    :target: https://github.com/DiamondLightSource/i22-bluesky/actions/workflows/docs.yml
    :alt: Docs CI

.. |coverage| image:: https://codecov.io/gh/DiamondLightSource/i22-bluesky/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/DiamondLightSource/i22-bluesky
    :alt: Test Coverage

.. |pypi_version| image:: https://img.shields.io/pypi/v/i22-bluesky.svg
    :target: https://pypi.org/project/i22-bluesky
    :alt: Latest PyPI version

.. |license| image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
    :target: https://opensource.org/licenses/Apache-2.0
    :alt: Apache License

..
    Anything below this line is used when viewing README.rst and will be replaced
    when included in index.rst

See https://DiamondLightSource.github.io/i22-bluesky for more detailed documentation.
