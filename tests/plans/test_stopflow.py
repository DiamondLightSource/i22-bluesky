from unittest.mock import patch

import numpy as np
import pytest
from bluesky.run_engine import RunEngine
from ophyd_async.panda import SeqTable, SeqTrigger

from i22_bluesky.plans.stopflow import count_stopflow_devices, stopflow_seq_table

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
            "repeats": np.array([1, 100, 200, 1], dtype=np.uint16),
            "trigger": [
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
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
            "repeats": np.array([1, 0, 200, 1], dtype=np.uint16),
            "trigger": [
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
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
)


@pytest.mark.parametrize(
    "generated_seq_table,expected_seq_table",
    SEQ_TABLE_TEST_CASES,
)
def test_stopflow_seq_table(
    generated_seq_table: SeqTable,
    expected_seq_table: SeqTable,
):
    np.testing.assert_equal(generated_seq_table, expected_seq_table)


def test_count_devices_calls_count():
    RE = RunEngine()
    expected_devices = [
        "saxs",
        "waxs",
        "i0",
        "it",
        "fswitch",
        "slits_1",
        "slits_2",
        "slits_3",
        "slits_5",
        "slits_6",
        "hfm",
        "vfm",
        "panda1",
    ]

    with patch("i22_bluesky.plans.stopflow.bp.count") as mock_count:
        RE(count_stopflow_devices())
    mock_count.assert_called_once_with(expected_devices, num=1)
