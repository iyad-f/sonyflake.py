from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest

from sonyflake.sonyflake import AsyncSonyflake, OverTimeLimit, _lower_16bit_private_ip


@pytest.mark.asyncio
class TestAsyncSonyflake:
    async def test_next_id(self) -> None:
        # TODO: Probably write some other kind of logic for this,
        # as this isnt consistent.
        sf = AsyncSonyflake(start_time=datetime.now(timezone.utc))

        sleep_time = 50
        await asyncio.sleep((sleep_time * sf._time_unit) / 1e9)

        id_ = await sf.next_id()

        actual_time = sf._time_part(id_)
        assert actual_time >= sleep_time
        assert actual_time <= sleep_time + 2
        assert sf._sequence_part(id_) == 0
        assert sf._machine_id_part(id_) == _lower_16bit_private_ip()

    async def test_next_id_in_sequence(self) -> None:
        now = datetime.now(timezone.utc)
        # This test may fail with a time unit of 1 millisecond,
        # as the system might not be able to generate (1 << bits_sequence) - 1
        # IDs within a single millisecond.
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
        num_ids = 1000
        ids: set[int] = set()

        async def generate_ids(sf: AsyncSonyflake) -> list[int]:
            return [await sf.next_id() for _ in range(num_ids)]

        tasks: list[asyncio.Task[list[int]]] = []
        for _ in range(num_cpus // 2):
            tasks.append(asyncio.create_task(generate_ids(sf1)))
            tasks.append(asyncio.create_task(generate_ids(sf2)))

        for coro in asyncio.as_completed(tasks):
            result = await coro
            for id_ in result:
                assert id_ not in ids
                ids.add(id_)

    async def test_next_id_raises_error(self) -> None:
        sf = AsyncSonyflake(start_time=datetime.now(timezone.utc))
        ticks_per_year = int(365 * 24 * 60 * 60 * 1e9) // sf._time_unit

        sf._start_time -= 174 * ticks_per_year
        await sf.next_id()

        sf._start_time -= 1 * ticks_per_year
        with pytest.raises(OverTimeLimit):
            await sf.next_id()

    async def test_to_time(self) -> None:
        start = datetime.now(timezone.utc)
        sf = AsyncSonyflake(time_unit=timedelta(milliseconds=1), start_time=start)

        id_ = await sf.next_id()

        tm = sf.to_time(id_)
        diff = tm - start

        assert timedelta(0) <= diff < timedelta(microseconds=sf._time_unit / 1000)
