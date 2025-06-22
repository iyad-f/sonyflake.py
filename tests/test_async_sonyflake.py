from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest

from sonyflake.sonyflake import AsyncSonyflake, OverTimeLimit, _lower_16bit_private_ip

import time
@pytest.mark.asyncio
class TestAsyncSonyflake:
    async def test_next_id(self) -> None:
        sf = AsyncSonyflake(start_time=datetime.now(timezone.utc))

        sleep_time = 50
        sleep_ns = sleep_time * sf._time_unit
        start = time.perf_counter_ns()

        while time.perf_counter_ns() - start < sleep_ns:
            pass

        id_ = await sf.next_id()

        actual_time = sf._time_part(id_)
        assert actual_time >= sleep_time
        # Adding a buffer of +2 to account for minor timing inconsistencies,
        # +1 was occasionally failing
        assert actual_time <= sleep_time + 1

        actual_sequence = sf._sequence_part(id_)
        assert actual_sequence == 0

        actual_machine_id = sf._machine_id_part(id_)
        assert actual_machine_id == _lower_16bit_private_ip()

    async def test_next_id_in_sequence(self) -> None:
        now = datetime.now(timezone.utc)
        sf = AsyncSonyflake(time_unit=timedelta(milliseconds=10), start_time=now)
        start_time = sf._to_internal_time(now)
        machine_id = _lower_16bit_private_ip()

        last_id = max_seq = 0

        current_time = start_time
        while current_time - start_time < 100:
            id_ = await sf.next_id()
            current_time = sf._to_internal_time(datetime.now(timezone.utc))

            assert id_ != last_id
            assert id_ > last_id
            last_id = id_

            parts = sf.decompose(id_)

            overtime = start_time + parts.time - current_time
            assert overtime <= 0

            max_seq = max(max_seq, parts.sequence)

            assert parts.machine_id == machine_id

        assert max_seq == (1 << sf._bits_sequence) - 1

    async def test_next_id_in_parallel(self) -> None:
        sf1 = AsyncSonyflake(machine_id=1)
        sf2 = AsyncSonyflake(machine_id=2)

        num_cpus = os.cpu_count() or 8
        num_id = 1000
        ids: set[int] = set()
        lock = asyncio.Lock()

        async def generate_ids(sf: AsyncSonyflake) -> None:
            for _ in range(num_id):
                id_ = await sf.next_id()
                async with lock:
                    assert id_ not in ids
                    ids.add(id_)

        await asyncio.gather(
            *[
                asyncio.gather(
                    generate_ids(sf1),
                    generate_ids(sf2),
                )
                for _ in range(num_cpus // 2)
            ]
        )

    @staticmethod
    def _pseudo_sleep(sf: AsyncSonyflake, period: timedelta) -> None:
        ticks = int(period.total_seconds() * 1e9) // sf._time_unit
        sf._start_time -= ticks

    async def test_next_id_raises_error(self) -> None:
        sf = AsyncSonyflake(start_time=datetime.now(timezone.utc))

        year = timedelta(days=365)
        self._pseudo_sleep(sf, 174 * year)
        await sf.next_id()

        self._pseudo_sleep(sf, 1 * year)

        with pytest.raises(OverTimeLimit):
            await sf.next_id()

    async def test_to_time(self) -> None:
        start = datetime.now(timezone.utc)
        sf = AsyncSonyflake(time_unit=timedelta(milliseconds=1), start_time=start)

        id_ = await sf.next_id()

        tm = sf.to_time(id_)
        diff = tm - start

        assert timedelta(0) <= diff < timedelta(microseconds=sf._time_unit / 1000)
