# Instantiate motors and encoders (reading fine yaw rotation) in GDA
# This should go in dodal.

# the diode motor is on a geo-brick
# the diode motor and the crystal motor need the same acceleration time
# (Dead reckoning)

# In ScanSpecSeqTableTriggerLogic make GPIO low-> high lines optional.

from functools import cache
from pathlib import Path

from dodal.device_manager import DeviceManager
from dodal.devices.motors import Stage, XYStage
from dodal.utils import BeamlinePrefix, get_beamline_name
from ophyd_async.core import (
    PathProvider,
    SingalR,
    StaticPathProvider,
    UUIDFilenameProvider,
)
from ophyd_async.epics.motor import Motor

BL = get_beamline_name("i22")
PREFIX = BeamlinePrefix(BL)

devices = DeviceManager()


@devices.fixture
@cache
def path_provider() -> PathProvider:
    return StaticPathProvider(UUIDFilenameProvider(), Path("/tmp"))


@devices.factory()
def usaxs_sample_stage() -> XYStage:
    return XYStage(
        prefix=f"{PREFIX.beamline_prefix}-MO-USAXS-01:",
        x_infix="XTRANS:",
        y_infix="YTRANS:",
    )


_X = "X"


class XYawFineYawStage(Stage):
    def __init__(
        self,
        prefix: str,
        name: str = "",
        x_infix: str = _X,
        yaw_infix: str = "YAW",
        fine_yaw_infix: str = "FINE_YAW",
        fine_yaw_rbv_infix: str = "FY",
    ):
        with self.add_children_as_readables():
            self.x = Motor(prefix + x_infix)
            self.yaw = Motor(prefix + yaw_infix)
            self.fine_yaw = Motor(prefix + fine_yaw_infix)
            self.fine_yaw_rbv = SingalR(prefix + fine_yaw_rbv_infix)
        super().__init__(name=name)


@devices.factory()
def upstream_crystal_tower() -> XYawFineYawStage:
    return XYawFineYawStage(
        prefix=f"{PREFIX.beamline_prefix}-MO-USAXS-01:",
        x_infix="UPSX",
        yaw_infix="UPSYAW",
        fine_yaw_infix="MCS2:YAW1",
        fine_yaw_rbv_infix="UPSFY",
    )


@devices.factory()
def downstream_crystal_tower() -> XYawFineYawStage:
    return XYawFineYawStage(
        prefix=f"{PREFIX.beamline_prefix}-MO-USAXS-01:",
        x_infix="DWNX",
        yaw_infix="DWNYAW",
        fine_yaw_infix="MCS2:YAW2",
        fine_yaw_rbv_infix="DWNFY",
    )
