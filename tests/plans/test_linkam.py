from pathlib import Path
from unittest.mock import ANY, Mock

import pytest
from bluesky.run_engine import RunEngine
from bluesky.utils import Msg
from ophyd_async.core import (
    DeviceCollector,
    DirectoryProvider,
    StaticDirectoryProvider,
    TriggerInfo,
)
from ophyd_async.epics.areadetector import PilatusDetector

from i22_bluesky.stubs import LinkamPathSegment, LinkamTrajectory
from i22_bluesky.stubs.linkam import capture_linkam_segment


def test_trajectory_validation_enforced():
    with pytest.raises(ValueError) as e:
        LinkamTrajectory(
            start=13.0, path=[], default_num_frames=-1, default_exposure=-0.7
        )
    for loc, msg, error in zip(
        (("path",), ("default_num_frames",), ("default_exposure",)),
        (
            "ensure this value has at least 1 items",
            "ensure this value is greater than 0",
            "ensure this value is greater than 0.0",
        ),
        e.value.errors(),
    ):
        assert error["loc"] == loc
        assert error["msg"] == msg


def test_segment_validation_enforced():
    with pytest.raises(ValueError) as e:
        LinkamPathSegment(stop=13.0, rate=-7.0, num=-3, num_frames=-2, exposure=-0.7)
    for loc, msg, error in zip(
        (("rate",), ("num",), ("num_frames",), ("exposure",)),
        (
            "ensure this value is greater than 0.0",
            "ensure this value is greater than 0",
            "ensure this value is greater than 0",
            "ensure this value is greater than 0.0",
        ),
        e.value.errors(),
    ):
        assert error["loc"] == loc
        assert error["msg"] == msg


def test_trajectory_root_validator():
    with pytest.raises(Exception) as e:
        LinkamTrajectory(
            start=13.0,
            path=[LinkamPathSegment(stop=13.0, rate=0.01, num=1)],
        )
    for msg, error in zip(
        (
            "Num frames not set for default and for some segment(s)!",
            "Exposure not set for default and for some segment(s)!",
        ),
        e.value.errors(),
    ):
        assert error["msg"] == msg


def test_segment_root_validator():
    with pytest.raises(ValueError, match="Must have set at least one of 'num', 'step'"):
        LinkamPathSegment(stop=13.0, rate=1.3)


@pytest.fixture
def stepped_trajectory():
    return LinkamTrajectory(
        start=0.0,
        path=[
            LinkamPathSegment(stop=50.0, rate=10.0, step=5.0),
            LinkamPathSegment(stop=0.0, rate=10.0, step=5.0),
        ],
        default_exposure=0.01,
        default_num_frames=1,
    )


@pytest.fixture
def directory_provider(tmp_path: Path) -> DirectoryProvider:
    return StaticDirectoryProvider(tmp_path)


@pytest.fixture
def mock_saxs(RE: RunEngine, directory_provider: DirectoryProvider) -> PilatusDetector:
    with DeviceCollector(mock=True):
        saxs = PilatusDetector("SAXS:", directory_provider)
    return saxs


@pytest.fixture
def mock_waxs(RE: RunEngine, directory_provider: DirectoryProvider) -> PilatusDetector:
    with DeviceCollector(mock=True):
        waxs = PilatusDetector("WAXS:", directory_provider)
    return waxs


def test_stepped_behaviour_to_all_temps_in_order(
    mock_saxs: PilatusDetector, mock_waxs: PilatusDetector
):
    mock_linkam = Mock()
    flyer = Mock()
    detectors = {mock_saxs, mock_waxs}
    msgs = list(
        capture_linkam_segment(
            mock_linkam,
            flyer,
            detectors,
            0.0,
            10.0,
            num=11,
            rate=10.0,
            num_frames=3,
            exposure=0.01,
        )
    )
    # Initial move to start of region
    previous_set_index = msgs.index(Msg("set", mock_linkam, 0.0, group=ANY)) + 1
    for temp in {0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0}:
        # We set to each temperature
        set_index = msgs.index(
            Msg("set", mock_linkam, temp, group=ANY), previous_set_index
        )
        # in order
        assert set_index > previous_set_index
        # and wait until the move is finished
        assert msgs[set_index + 1] == Msg("wait", group=msgs[set_index].kwargs["group"])
        previous_set_index = set_index


def test_flown_behaviour_sequence_table(
    mock_saxs: PilatusDetector, mock_waxs: PilatusDetector
):
    mock_linkam = Mock()
    flyer = Mock()
    detectors = {mock_saxs, mock_waxs}
    msgs = list(
        capture_linkam_segment(
            mock_linkam,
            flyer,
            detectors,
            0.0,
            10.0,
            num=11,
            rate=10.0,
            num_frames=3,
            exposure=0.01,
            fly=True,
        )
    )
    same_trigger_info = None
    for device in detectors:
        prepare_index = msgs.index(Msg("prepare", device, ANY, group=ANY))
        prepare_msg = msgs[prepare_index]
        trigger_info = prepare_msg[2][0]  # Unwrap tuple
        assert isinstance(trigger_info, TriggerInfo)
        if same_trigger_info is None:
            same_trigger_info = trigger_info
        else:
            assert trigger_info == same_trigger_info
