import asyncio
from typing import List

import bluesky.plan_stubs as bps
from dls_bluesky_core.core import in_micros
from dodal.common.types import MsgGenerator
from ophyd_async.core import (
    AsyncStatus,
    DetectorTrigger,
    HardwareTriggeredFlyable,
    wait_for_value,
)
from ophyd_async.core.flyer import TriggerInfo, TriggerLogic
from ophyd_async.panda import (
    PandA,
    SeqTableRow,
    seq_table_from_rows,
)

from i22_bluesky.common.types import CollectableFlyable
from i22_bluesky.panda.fly_scanning import RepeatedTrigger
from i22_bluesky.stubs.fly import prepare_all_with_trigger
from i22_bluesky.stubs.linkam import fly_and_collect


class PandARepeatedTriggerLogic(TriggerLogic[RepeatedTrigger]):
    trigger = DetectorTrigger.constant_gate

    def __init__(
        self, panda: PandA, shutter_time: float = 0, *, sequence_block: int = 1
    ):
        self.seq = panda.seq[sequence_block]
        self.shutter_time = shutter_time

    def trigger_info(self, value: RepeatedTrigger) -> TriggerInfo:
        return TriggerInfo(
            num=value.num * value.repeats,
            trigger=DetectorTrigger.constant_gate,
            deadtime=value.deadtime,
            livetime=value.width,
        )

    def prepare(
        self,
        value: RepeatedTrigger,
    ) -> AsyncStatus:
        return AsyncStatus(self._prepare(value))

    async def _prepare(self, value: RepeatedTrigger):
        table = seq_table_from_rows(
            SeqTableRow(
                repeats=value.num,
                time1=in_micros(value.width),
                outa1=True,
                time2=in_micros(value.deadtime),
            ),
        )
        await asyncio.gather(
            self.seq.prescale_units.set("us"),
            self.seq.enable.set("ZERO"),
        )
        await asyncio.gather(
            self.seq.prescale.set(1),
            self.seq.repeats.set(value.repeats),
            self.seq.table.set(table),
        )

    async def start(self):
        await self.seq.enable.set("ONE")
        await wait_for_value(self.seq.active, 1, timeout=1)
        await wait_for_value(self.seq.active, 0, timeout=None)

    async def stop(self):
        await self.seq.enable.set("ZERO")
        await wait_for_value(self.seq.active, 0, timeout=1)


# TODO: Make non-flyer signature to allow non-flying with non-flying devices
def fly_count(
    panda: PandA,
    devices: List[CollectableFlyable],
    exposure: float = 1,
    deadtime: float = 2e-3,
    num_frames: int = 1,
    period: float = 0,
    num_collections: int = 6,
) -> MsgGenerator:
    # Take num_frames from each devices periodically
    batches = RepeatedTrigger(
        num=num_frames,
        width=exposure,
        deadtime=deadtime,
        repeats=num_collections,
        period=period,
    )

    flyer = HardwareTriggeredFlyable(
        PandARepeatedTriggerLogic(panda, shutter_time=exposure),
        configuration_signals=[],
    )

    yield from bps.stage_all(*devices)
    yield from bps.open_run()
    yield from prepare_all_with_trigger(flyer, devices, batches)
    yield from fly_and_collect(flyer, devices)
    yield from bps.close_run()
    yield from bps.unstage_all(*devices)
