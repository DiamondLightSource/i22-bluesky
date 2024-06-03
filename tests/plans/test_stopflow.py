import numpy as np
import pytest
from ophyd_async.panda import SeqTable, SeqTrigger

from i22_bluesky.plans.stopflow import (
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
            "repeats": np.array([1, 100, 1, 1, 200, 1], dtype=np.uint16),
            "trigger": [
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            "position": np.array([0, 0, 0, 0, 0, 0], dtype=np.int32),
            "time1": np.array([0, 50000, 4000, 4000, 50000, 0], dtype=np.uint32),
            # "outa1": np.array([False, True, False, False, True, False]),
            "outa1": np.array([False,True, False,True,True, False]),
            "outb1": np.array([False, True, False, False, True, False]),
            "outc1": np.array([False, False, False, False, False, False]),
            "outd1": np.array([False, False, False, False, False, False]),
            "oute1": np.array([False, False, False, False, False, False]),
            "outf1": np.array([False, False, False, False, False, False]),
            "time2": np.array([4000, 2280, 0, 0, 2280, 4000], dtype=np.uint32),
            "outa2": np.array([True, True, False, False, True, False]),
            "outb2": np.array([False, False, False, False, False, False]),
            "outc2": np.array([False, False, False, False, False, False]),
            "outd2": np.array([False, False, False, False, False, False]),
            "oute2": np.array([False, False, False, False, False, False]),
            "outf2": np.array([False, False, False, False, False, False]),
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
            "repeats": np.array([1, 0,1, 1, 200, 1], dtype=np.uint16),
            "trigger": [
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.BITA_1,
                SeqTrigger.IMMEDIATE,
                SeqTrigger.IMMEDIATE,
            ],
            "position": np.array([0, 0, 0,0, 0, 0], dtype=np.int32),
            "time1": np.array([0, 50000,4000, 4000, 50000, 0], dtype=np.uint32),
            "outa1": np.array([False, True, False, True, True, False]),
            "outb1": np.array([False, True, False, False, True, False]),
            "outc1": np.array([False, False, False, False, False, False]),
            "outd1": np.array([False, False, False, False, False, False]),
            "oute1": np.array([False, False, False, False, False, False]),
            "outf1": np.array([False, False, False, False, False, False]),
            "time2": np.array([4000, 2280, 0, 0, 2280, 4000], dtype=np.uint32),
            "outa2": np.array([True, True, False, False, True, False]),
            "outb2": np.array([False, False,False, False, False, False]),
            "outc2": np.array([False, False,False, False, False, False]),
            "outd2": np.array([False, False,False, False, False, False]),
            "oute2": np.array([False, False,False, False, False, False]),
            "outf2": np.array([False, False,False, False, False, False]),
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
