import asyncio
from dataclasses import dataclass

from dodal.common.maths import in_micros
from ophyd_async.core import DetectorTrigger, TriggerInfo, TriggerLogic, wait_for_value
from ophyd_async.panda import SeqBlock, SeqTableRow, seq_table_from_rows


@dataclass
class RepeatedTrigger:
    num: int
    width: float
    deadtime: float
    repeats: int = 1
    period: float = 0.0


class PandARepeatedTriggerLogic(TriggerLogic[RepeatedTrigger]):
    trigger = DetectorTrigger.constant_gate

    def __init__(self, seq: SeqBlock, shutter_time: float = 0) -> None:
        self.seq = seq
        self.shutter_time = shutter_time

    def trigger_info(self, value: RepeatedTrigger) -> TriggerInfo:
        return TriggerInfo(
            num=value.num * value.repeats,
            trigger=DetectorTrigger.constant_gate,
            deadtime=value.deadtime,
            livetime=value.width,
        )

    async def prepare(self, value: RepeatedTrigger):
        trigger_time = value.num * (value.width + value.deadtime)
        pre_delay = max(value.period - 2 * self.shutter_time - trigger_time, 0)
        table = seq_table_from_rows(
            # Wait for pre-delay then open shutter
            SeqTableRow(
                time1=in_micros(pre_delay),
                time2=in_micros(self.shutter_time),
                outa2=True,
            ),
            # Keeping shutter open, do N triggers
            SeqTableRow(
                repeats=value.num,
                time1=in_micros(value.width),
                outa1=True,
                outb1=True,
                time2=in_micros(value.deadtime),
                outa2=True,
            ),
            # Add the shutter close
            SeqTableRow(time2=in_micros(self.shutter_time)),
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
