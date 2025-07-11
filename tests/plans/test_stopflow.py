import asyncio
from typing import cast
from unittest.mock import Mock, patch

import numpy as np
import pytest
from bluesky.protocols import Readable
from bluesky.run_engine import RunEngine
from dodal.beamlines.i22 import i0, it, panda1, saxs, waxs
from ophyd_async.core import StandardDetector
from ophyd_async.epics.adcore import ADHDFWriter
from ophyd_async.epics.adpilatus import PilatusDetector, PilatusDriverIO
from ophyd_async.fastcs.panda import (
    DatasetTable,
    PandaHdf5DatasetType,
    SeqTable,
    SeqTrigger,
)
from ophyd_async.testing import callback_on_mock_put, set_mock_value

from i22_bluesky.plans import check_detectors_for_stopflow, stopflow
from i22_bluesky.plans.stopflow import (
    raise_for_minimum_exposure_times,
)
from i22_bluesky.stubs.stopflow import stopflow_seq_table

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
        SeqTable(
            repeats=np.array([1, 100, 1, 199, 1], dtype=np.uint16),
            trigger=[
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            position=np.array([0, 0, 0, 0, 0], dtype=np.int32),
            time1=np.array([0, 50000, 50000, 50000, 0], dtype=np.uint32),
            outa1=np.array([False, True, True, True, False]),
            outb1=np.array([False, True, True, True, False]),
            outc1=np.array([False, False, False, False, False]),
            outd1=np.array([False, False, False, False, False]),
            oute1=np.array([False, False, False, False, False]),
            outf1=np.array([False, False, False, False, False]),
            time2=np.array([4000, 2280, 2280, 2280, 4000], dtype=np.uint32),
            outa2=np.array([True, True, True, True, False]),
            outb2=np.array([False, False, False, False, False]),
            outc2=np.array([False, False, False, False, False]),
            outd2=np.array([False, False, False, False, False]),
            oute2=np.array([False, False, False, False, False]),
            outf2=np.array([False, False, False, False, False]),
        ),
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
        SeqTable(
            repeats=np.array([1, 1, 199, 1], dtype=np.uint16),
            trigger=[
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            position=np.array([0, 0, 0, 0], dtype=np.int32),
            time1=np.array([0, 50000, 50000, 0], dtype=np.uint32),
            outa1=np.array([False, True, True, False]),
            outb1=np.array([False, True, True, False]),
            outc1=np.array([False, False, False, False]),
            outd1=np.array([False, False, False, False]),
            oute1=np.array([False, False, False, False]),
            outf1=np.array([False, False, False, False]),
            time2=np.array([4000, 2280, 2280, 4000], dtype=np.uint32),
            outa2=np.array([True, True, True, False]),
            outb2=np.array([False, False, False, False]),
            outc2=np.array([False, False, False, False]),
            outd2=np.array([False, False, False, False]),
            oute2=np.array([False, False, False, False]),
            outf2=np.array([False, False, False, False]),
        ),
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
        SeqTable(
            repeats=np.array([1, 200, 1], dtype=np.uint16),
            trigger=[
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            position=np.array([0, 0, 0], dtype=np.int32),
            time1=np.array([0, 50000, 0], dtype=np.uint32),
            outa1=np.array([False, True, False]),
            outb1=np.array([False, True, False]),
            outc1=np.array([False, False, False]),
            outd1=np.array([False, False, False]),
            oute1=np.array([False, False, False]),
            outf1=np.array([False, False, False]),
            time2=np.array([4000, 2280, 4000], dtype=np.uint32),
            outa2=np.array([True, True, False]),
            outb2=np.array([False, False, False]),
            outc2=np.array([False, False, False]),
            outd2=np.array([False, False, False]),
            oute2=np.array([False, False, False]),
            outf2=np.array([False, False, False]),
        ),
    ),
    (
        stopflow_seq_table(
            pre_stop_frames=1,
            post_stop_frames=0,
            exposure=0.05,
            shutter_time=4e-3,
            deadtime=2.28e-3,
            period=0.0,
        ),
        SeqTable(
            repeats=np.array([1, 1, 1], dtype=np.uint16),
            trigger=[
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            position=np.array([0, 0, 0], dtype=np.int32),
            time1=np.array([0, 50000, 0], dtype=np.uint32),
            outa1=np.array([False, True, False]),
            outb1=np.array([False, True, False]),
            outc1=np.array([False, False, False]),
            outd1=np.array([False, False, False]),
            oute1=np.array([False, False, False]),
            outf1=np.array([False, False, False]),
            time2=np.array([4000, 2280, 4000], dtype=np.uint32),
            outa2=np.array([True, True, False]),
            outb2=np.array([False, False, False]),
            outc2=np.array([False, False, False]),
            outd2=np.array([False, False, False]),
            oute2=np.array([False, False, False]),
            outf2=np.array([False, False, False]),
        ),
    ),
    (
        stopflow_seq_table(
            pre_stop_frames=0,
            post_stop_frames=1,
            exposure=0.05,
            shutter_time=4e-3,
            deadtime=2.28e-3,
            period=0.0,
        ),
        SeqTable(
            repeats=np.array([1, 1, 1], dtype=np.uint16),
            trigger=[
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
                SeqTrigger.IMMEDIATE,
            ],
            position=np.array([0, 0, 0], dtype=np.int32),
            time1=np.array([0, 50000, 0], dtype=np.uint32),
            outa1=np.array([False, True, False]),
            outb1=np.array([False, True, False]),
            outc1=np.array([False, False, False]),
            outd1=np.array([False, False, False]),
            oute1=np.array([False, False, False]),
            outf1=np.array([False, False, False]),
            time2=np.array([4000, 2280, 4000], dtype=np.uint32),
            outa2=np.array([True, True, False]),
            outb2=np.array([False, False, False]),
            outc2=np.array([False, False, False]),
            outd2=np.array([False, False, False]),
            oute2=np.array([False, False, False]),
            outf2=np.array([False, False, False]),
        ),
    ),
    (
        stopflow_seq_table(
            pre_stop_frames=1,
            post_stop_frames=1,
            exposure=0.05,
            shutter_time=4e-3,
            deadtime=2.28e-3,
            period=0.0,
        ),
        SeqTable(
            repeats=np.array([1, 1, 1, 1], dtype=np.uint16),
            trigger=[
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
                SeqTrigger.IMMEDIATE,
            ],
            position=np.array([0, 0, 0, 0], dtype=np.int32),
            time1=np.array([0, 50000, 50000, 0], dtype=np.uint32),
            outa1=np.array([False, True, True, False]),
            outb1=np.array([False, True, True, False]),
            outc1=np.array([False, False, False, False]),
            outd1=np.array([False, False, False, False]),
            oute1=np.array([False, False, False, False]),
            outf1=np.array([False, False, False, False]),
            time2=np.array([4000, 2280, 2280, 4000], dtype=np.uint32),
            outa2=np.array([True, True, True, False]),
            outb2=np.array([False, False, False, False]),
            outc2=np.array([False, False, False, False]),
            outd2=np.array([False, False, False, False]),
            oute2=np.array([False, False, False, False]),
            outf2=np.array([False, False, False, False]),
        ),
    ),
    (
        stopflow_seq_table(
            pre_stop_frames=0,
            post_stop_frames=0,
            exposure=0.05,
            shutter_time=4e-3,
            deadtime=2.28e-3,
            period=0.0,
        ),
        SeqTable(
            repeats=np.array([1, 1], dtype=np.uint16),
            trigger=[
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            position=np.array([0, 0], dtype=np.int32),
            time1=np.array([0, 0], dtype=np.uint32),
            outa1=np.array([False, False]),
            outb1=np.array([False, False]),
            outc1=np.array([False, False]),
            outd1=np.array([False, False]),
            oute1=np.array([False, False]),
            outf1=np.array([False, False]),
            time2=np.array([4000, 4000], dtype=np.uint32),
            outa2=np.array([True, False]),
            outb2=np.array([False, False]),
            outc2=np.array([False, False]),
            outd2=np.array([False, False]),
            oute2=np.array([False, False]),
            outf2=np.array([False, False]),
        ),
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
    for element in generated_seq_table.__dict__:
        if element == "trigger":
            assert getattr(expected_seq_table, element) == getattr(
                generated_seq_table, element
            )
        else:
            assert all(
                getattr(expected_seq_table, element)
                == getattr(generated_seq_table, element)
            )


@pytest.mark.xfail(reason="Strange import behavior, to be investigated")
def test_check_detectors_for_stopflow_excludes_tetramms(RE: RunEngine):
    devices: set[Readable] = {
        saxs(mock=True),
        waxs(mock=True),
        i0(mock=True),
        it(mock=True),
    }

    with patch("i22_bluesky.plans.stopflow.bp.count") as mock_count:
        RE(check_detectors_for_stopflow(devices=devices))
    mock_count.assert_called_once_with(
        {
            saxs(mock=True),
            waxs(mock=True),
        },
        num=1,
    )


@pytest.mark.xfail(reason="Test WIP, can't quite simulate triggering behavior")
def test_stopflow_plan(RE: RunEngine):
    pilatuses: set[PilatusDetector] = {
        saxs(mock=True),
        waxs(mock=True),
    }
    detectors: set[StandardDetector] = {
        saxs(mock=True),
        waxs(mock=True),
        i0(mock=True),
        it(mock=True),
    }
    panda = panda1(mock=True)
    set_mock_value(
        panda.data.datasets,
        DatasetTable(
            name=["time"],
            dtype=[PandaHdf5DatasetType.FLOAT_64],
        ),
    )

    for pilatus in pilatuses:
        set_mock_value(cast(PilatusDriverIO, pilatus.driver).armed, True)
    for detector in detectors:
        set_mock_value(
            cast(ADHDFWriter, detector._writer).fileio.file_path_exists, True
        )

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
        lambda v, _: asyncio.create_task(simulate_triggers()),
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
