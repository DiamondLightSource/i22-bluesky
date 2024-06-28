import asyncio
from unittest.mock import Mock, patch

import numpy as np
import pytest
from bluesky.run_engine import RunEngine
from dodal.beamlines.i22 import i0, it, saxs, waxs
from dodal.devices.tetramm import TetrammDetector
from ophyd_async.core import (
    callback_on_mock_put,
    set_mock_value,
)
from ophyd_async.core.detector import StandardDetector
from ophyd_async.epics.areadetector.pilatus import PilatusDetector
from ophyd_async.panda import SeqTable, SeqTrigger
from ophyd_async.panda._table import DatasetTable, PandaHdf5DatasetType

from i22_bluesky.plans import check_detectors_for_stopflow, stopflow
from i22_bluesky.plans.stopflow import (
    raise_for_minimum_exposure_times,
    stopflow_seq_table,
)

SEQ_TABLE_TEST_CASES: tuple[tuple[SeqTable, SeqTable], ...] = (
    # Very simple case, 1 frame on each side and 1 second
    (
        stopflow_seq_table(
            pre_stop_frames=100,
            post_stop_frames=200,
            exposure=0.05,
            shutter_time=4e-3,
            deadtime=2.28e-3,
            period=0.0,
        ),
        {
            "repeats": np.array([1, 100, 1, 199, 1], dtype=np.uint16),
            "trigger": [
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            "position": np.array([0, 0, 0, 0, 0], dtype=np.int32),
            "time1": np.array([0, 50000, 50000, 50000, 0], dtype=np.uint32),
            "outa1": np.array([False, True, True, True, False]),
            "outb1": np.array([False, True, True, True, False]),
            "outc1": np.array([False, False, False, False, False]),
            "outd1": np.array([False, False, False, False, False]),
            "oute1": np.array([False, False, False, False, False]),
            "outf1": np.array([False, False, False, False, False]),
            "time2": np.array([4000, 2280, 2280, 2280, 4000], dtype=np.uint32),
            "outa2": np.array([True, True, True, True, False]),
            "outb2": np.array([False, False, False, False, False]),
            "outc2": np.array([False, False, False, False, False]),
            "outd2": np.array([False, False, False, False, False]),
            "oute2": np.array([False, False, False, False, False]),
            "outf2": np.array([False, False, False, False, False]),
        },
    ),
    # Same but taking no frames at the start
    (
        stopflow_seq_table(
            pre_stop_frames=0,
            post_stop_frames=200,
            exposure=0.05,
            shutter_time=4e-3,
            deadtime=2.28e-3,
            period=0.0,
        ),
        {
            "repeats": np.array([1, 1, 199, 1], dtype=np.uint16),
            "trigger": [
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            "position": np.array([0, 0, 0, 0], dtype=np.int32),
            "time1": np.array([0, 50000, 50000, 0], dtype=np.uint32),
            "outa1": np.array([False, True, True, False]),
            "outb1": np.array([False, True, True, False]),
            "outc1": np.array([False, False, False, False]),
            "outd1": np.array([False, False, False, False]),
            "oute1": np.array([False, False, False, False]),
            "outf1": np.array([False, False, False, False]),
            "time2": np.array([4000, 2280, 2280, 4000], dtype=np.uint32),
            "outa2": np.array([True, True, True, False]),
            "outb2": np.array([False, False, False, False]),
            "outc2": np.array([False, False, False, False]),
            "outd2": np.array([False, False, False, False]),
            "oute2": np.array([False, False, False, False]),
            "outf2": np.array([False, False, False, False]),
        },
    ),
    (
        stopflow_seq_table(
            pre_stop_frames=200,
            post_stop_frames=0,
            exposure=0.05,
            shutter_time=4e-3,
            deadtime=2.28e-3,
            period=0.0,
        ),
        {
            "repeats": np.array([1, 200, 1], dtype=np.uint16),
            "trigger": [
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            "position": np.array([0, 0, 0], dtype=np.int32),
            "time1": np.array([0, 50000, 0], dtype=np.uint32),
            "outa1": np.array([False, True, False]),
            "outb1": np.array([False, True, False]),
            "outc1": np.array([False, False, False]),
            "outd1": np.array([False, False, False]),
            "oute1": np.array([False, False, False]),
            "outf1": np.array([False, False, False]),
            "time2": np.array([4000, 2280, 4000], dtype=np.uint32),
            "outa2": np.array([True, True, False]),
            "outb2": np.array([False, False, False]),
            "outc2": np.array([False, False, False]),
            "outd2": np.array([False, False, False]),
            "oute2": np.array([False, False, False]),
            "outf2": np.array([False, False, False]),
        },
    ),
)


@pytest.mark.parametrize("exposure", [0.04, 0.01, 0.001])
def test_exposure_time_raises(exposure: float):
    detectors: set[StandardDetector] = set()
    for name in {"saxs", "waxs", "oav", "i0", "it"}:
        mock = Mock()
        mock.name = name
        detectors.update({mock})

    with pytest.raises(KeyError):
        raise_for_minimum_exposure_times(exposure, detectors)


@pytest.mark.parametrize("exposure", [1 / 22.0, 0.05, 0.5, 1.0, 10.0])
def test_exposure_time_does_not_raise(exposure: float):
    detectors: set[StandardDetector] = set()
    for name in {"saxs", "waxs", "oav", "i0", "it"}:
        mock = Mock()
        mock.name = name
        detectors.update({mock})

    raise_for_minimum_exposure_times(exposure, detectors)


@pytest.mark.parametrize(
    "generated_seq_table,expected_seq_table",
    SEQ_TABLE_TEST_CASES,
)
def test_stopflow_seq_table(
    generated_seq_table: SeqTable,
    expected_seq_table: SeqTable,
):
    np.testing.assert_equal(expected_seq_table, generated_seq_table)


@pytest.mark.xfail(reason="Strange import behavior, to be investigated")
def test_check_detectors_for_stopflow_excludes_tetramms():
    RE = RunEngine()

    expected_detectors = {
        saxs(fake_with_ophyd_sim=True),
        waxs(fake_with_ophyd_sim=True),
    }

    detectors = expected_detectors + {
        i0(fake_with_ophyd_sim=True),
        it(fake_with_ophyd_sim=True),
    }

    with patch("i22_bluesky.plans.stopflow.bp.count") as mock_count:
        RE(check_detectors_for_stopflow(devices=detectors))
    mock_count.assert_called_once_with(expected_detectors, num=1)


@pytest.mark.xfail(reason="Test WIP, can't quite simulate triggering behavior")
def test_stopflow_plan():
    from dodal.beamlines.i22 import i0, it, panda1, saxs, waxs

    RE = RunEngine()

    pilatuses: set[StandardDetector] = {
        saxs(fake_with_ophyd_sim=True),
        waxs(fake_with_ophyd_sim=True),
    }
    detectors: set[PilatusDetector | TetrammDetector] = pilatuses + {
        i0(fake_with_ophyd_sim=True),
        it(fake_with_ophyd_sim=True),
    }
    panda = panda1(fake_with_ophyd_sim=True)
    set_mock_value(
        panda.data.datasets,
        DatasetTable(
            name=np.array(["time"]),
            hdf5_type=[PandaHdf5DatasetType.FLOAT_64],
        ),
    )

    for pilatus in pilatuses:
        set_mock_value(pilatus.drv.armed_for_triggers, True)
    for detector in detectors:
        set_mock_value(detector.hdf.file_path_exists, True)

    async def simulate_triggers():
        set_mock_value(panda.pcap.active, True)
        set_mock_value(panda.seq[1].active, True)
        await asyncio.sleep(0.01)
        for detector in detectors:
            set_mock_value(detector.hdf.num_captured, 20)
        await asyncio.sleep(0.01)
        set_mock_value(panda.pcap.active, False)
        set_mock_value(panda.seq[1].active, False)
        await asyncio.sleep(0.01)

    callback_on_mock_put(
        panda.pcap.arm,
        lambda v, **_: asyncio.create_task(simulate_triggers()),
    )

    RE(
        stopflow(
            exposure=0.1,
            post_stop_frames=10,
            pre_stop_frames=10,
            shutter_time=4e-3,
            panda=panda,
            detectors=detectors,
            baseline=set(),
        )
    )


# DEFAULT OTHER PARAMS
#             exposure=0.05,
#             shutter_time=4e-3,
#             deadtime=2.28e-3,
#             period=0.0,


def test_pre_1_post_0():
    o = stopflow_seq_table(
        pre_stop_frames=1,
        post_stop_frames=0,
        exposure=0.05,
        shutter_time=4e-3,
        deadtime=2.28e-3,
        period=0.0,
    )
    repeats = o["repeats"]
    np.testing.assert_equal(repeats, np.array([1, 1, 1]))


def test_pre_0_post_1():
    raise AssertionError("not implemented")


def test_pre_1_post_1():
    raise AssertionError("not implemented")


def test_pre_0_post_0():
    raise AssertionError("not implemented")


def test_pre_200_post_0():
    raise AssertionError("not implemented")
