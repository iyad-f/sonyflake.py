from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

from sonyflake.sonyflake import OverTimeLimit, Sonyflake, _lower_16bit_private_ip

if TYPE_CHECKING:
    from concurrent.futures import Future


class TestSonyflake:
    def test_next_id(self) -> None:
        # TODO: Probably write some other kind of logic for this,
        # as this isnt consistent.
        sf = Sonyflake(start_time=datetime.now(timezone.utc))

        sleep_time = 50
        time.sleep((sleep_time * sf._time_unit) / 1e9)

        id_ = sf.next_id()

        actual_time = sf._time_part(id_)
        assert actual_time >= sleep_time
        assert actual_time <= sleep_time + 2
        assert sf._sequence_part(id_) == 0
        assert sf._machine_id_part(id_) == _lower_16bit_private_ip()

    def test_next_id_in_sequence(self) -> None:
        now = datetime.now(timezone.utc)
        # This test may fail with a time unit of 1 millisecond,
        # as the system might not be able to generate (1 << bits_sequence) - 1
        # IDs within a single millisecond.
        sf = Sonyflake(time_unit=timedelta(milliseconds=10), start_time=now)
        start_time = sf._to_internal_time(now)
        machine_id = _lower_16bit_private_ip()

        last_id = max_seq = 0

        current_time = start_time
        while current_time - start_time < 100:
            id_ = sf.next_id()
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

    def test_next_id_in_parallel(self) -> None:
        sf1 = Sonyflake(machine_id=1)
        sf2 = Sonyflake(machine_id=2)

        num_cpus = os.cpu_count() or 8
        num_id = 1000
        ids: set[int] = set()

        def generate_ids(sf: Sonyflake) -> list[int]:
            return [sf.next_id() for _ in range(num_id)]

        with ThreadPoolExecutor(max_workers=num_cpus) as executor:
            futures: list[Future[list[int]]] = []
            for _ in range(num_cpus // 2):
                futures.append(executor.submit(generate_ids, sf1))
                futures.append(executor.submit(generate_ids, sf2))

            for future in as_completed(futures):
                for id_ in future.result():
                    assert id_ not in ids
                    ids.add(id_)

    def test_next_id_raises_error(self) -> None:
        sf = Sonyflake(start_time=datetime.now(timezone.utc))
        ticks_per_year = int(365 * 24 * 60 * 60 * 1e9) // sf._time_unit

        sf._start_time -= 174 * ticks_per_year
        sf.next_id()

        sf._start_time -= 1 * ticks_per_year
        with pytest.raises(OverTimeLimit):
            sf.next_id()

    def test_to_time(self) -> None:
        start = datetime.now(timezone.utc)
        sf = Sonyflake(time_unit=timedelta(milliseconds=1), start_time=start)

        id_ = sf.next_id()

        tm = sf.to_time(id_)
        diff = tm - start

        assert timedelta(0) <= diff < timedelta(microseconds=sf._time_unit / 1000)
