from pathlib import Path
from unittest.mock import ANY, Mock

import numpy as np
import pytest
from bluesky.run_engine import RunEngine
from bluesky.utils import Msg
from ophyd_async.core import (
    PathProvider,
    StaticFilenameProvider,
    StaticPathProvider,
    TriggerInfo,
    init_devices,
)
from ophyd_async.epics.adpilatus import PilatusDetector
from pydantic import ValidationError

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
            "List should have at least 1 item after validation, not 0",
            "Input should be greater than 0",
            "Input should be greater than 0",
        ),
        e.value.errors(),
        strict=False,
    ):
        assert error["loc"] == loc
        assert error["msg"] == msg


def test_segment_validation_enforced():
    with pytest.raises(ValueError) as e:
        LinkamPathSegment(stop=13.0, rate=-7.0, num=-3, num_frames=-2, exposure=-0.7)
    for loc, msg, error in zip(
        (("rate",), ("num",), ("num_frames",), ("exposure",)),
        (
            "Input should be greater than 0",
            "Input should be greater than 0",
            "Input should be greater than 0",
            "Input should be greater than 0",
        ),
        e.value.errors(),
        strict=False,
    ):
        assert error["loc"] == loc
        assert error["msg"] == msg


def test_trajectory_model_validator():
    with pytest.raises(ValidationError) as e:
        LinkamTrajectory(
            start=13.0,
            path=[LinkamPathSegment(stop=13.0, rate=0.01, num=1)],
        )
    for msg, error in zip(
        (
            "Number of frames not set for default and for some segment(s)!",
            "Exposure not set for default and for some segment(s)!",
        ),
        e.value.errors(),
        strict=False,
    ):
        assert msg in error["msg"]


def test_segment_model_validator():
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
def name_provider(name="foo"):
    return StaticFilenameProvider(name)


@pytest.fixture
def path_provider(name_provider, tmp_path: Path) -> PathProvider:
    return StaticPathProvider(name_provider, tmp_path)


@pytest.fixture
def mock_saxs(RE: RunEngine, path_provider: PathProvider) -> PilatusDetector:
    with init_devices(mock=True):
        saxs = PilatusDetector("SAXS:", path_provider)
    return saxs


@pytest.fixture
def mock_waxs(RE: RunEngine, path_provider: PathProvider) -> PilatusDetector:
    with init_devices(mock=True):
        waxs = PilatusDetector("WAXS:", path_provider)
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
    for temp in np.linspace(0, 10, num=11):
        # We set to each temperature
        set_index = msgs.index(
            Msg("set", mock_linkam, temp, group=ANY), previous_set_index
        )
        # in order
        assert set_index > previous_set_index
        # and wait until the move is finished
        wait_message = msgs[set_index + 1]
        assert wait_message.command == "wait"
        assert wait_message.kwargs["group"] == msgs[set_index].kwargs["group"]
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
