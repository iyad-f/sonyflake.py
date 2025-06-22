# sonyflake.py

Sonyflake is a distributed unique ID generator inspired by [Twitter's Snoflake](https://blog.twitter.com/2010/announcing-snowflake).

This is a python rewrite of the original [sony/sonyflake](https://github.com/sony/sonyflake) project, written in Go.

Sonyflake focuses on lifetime and performance on many host/core environment. So it has a different bit assignment from Snowflake. By default, a Sonyflake ID is composed of

    39 bits for time in units of 10 msec
     8 bits for a sequence number
    16 bits for a machine id

As a result, Sonyflake has the following advantages and disadvantages:

- The lifetime (174 years) is longer than that of Snowflake (69 years)
- It can work in more distributed machines (2^16) than Snowflake (2^10)
- It can generate 2^8 IDs oer 10 msec at most in a single instance (fewer than Snowflake)

However, if you want more generation rate in a single host,
you can easily run multiple Sonyflake or AsyncSonyflake instances in parallel using threads or asyncio tasks.

In addition, you can adjust the lifetime and generation rate of Sonyflake
by customizing the bit assignment and the time unit.

## Installation

**Python 3.10 or higher is required**

### Stable

```sh
# Linux/macOS
python -m pip install -U sonyflake.py

# Windows
py -3 -m pip install -U sonyflake.py
```

### Development

```sh
# Linux/macOS
python -m pip install -U "sonyflake.py @ git+https://github.com/iyad-f/sonyflake.py"

# Windows
py -3 -m pip install -U "sonyflake.py @ git+https://github.com/iyad-f/sonyflake.py"
```

## Usage

Creating a new Sonyflake instance.

### Sync

```py
from sonyflake import Sonyflake

sf = Sonyflake()
```

### Async

```py
from sonyflake import AsyncSonyflake

sf = AsyncSonyflake()
```

You can configure Sonyflake with the following options:

- bits_sequence is the bit length of a sequence number.
  If bits_sequence is not provided, the default bit length is used, which is 8.
  If bits_sequence is 31 or more, an error is raised.

- bits_machine_id is the bit length of a machin ID.
  If bits_machine_id is not provided, the default bit length is used, which is 16.
  if bits_machine_id is 31 or more, an error is raised.

- time_unit is the time unit of Sonyflake.
  If time_unit is not provided, the default time unit is used, which is 10msex.
  If time_unit is less than a millsecond an error is raised.

- start_time is the time since which the Sonyflake time is defined as the elapsed time .
  If start_time is not provided, the start time of the Sonyflake instance is set to "2025-01-01 00:00:00 +0000 UTC".
  If start_time is not before the current time an error is raised.

- machine_id is the unique ID of a Sonyflake instance.
  If machine_id is not provided, the default machine_id is used, which is the lower 16 bits of the private IP address.

- check_machine_id validates the uniqueness of a machine ID.
  If check_machine_id returns false an error is raised.
  If check_machine_id is not provided, no validation is done.

The bit length of time is calculated by 63 - bits_sequence - bits_machine_id.
If it is less than 32, an error is raised.

In order to get a new unique ID, you just have to call the method next_id.

### Sync

```py
from sonyflake import Sonyflake

sf = Sonyflake()
next_id = sf.next_id()
print(next_id)
```

### Async

```py
import asyncio
from sonyflake import AsyncSonyflake

async def main():
    sf = AsyncSonyflake()
    next_id = await sf.next_id()
    print(next_id)

asyncio.run(main())
```

next_id can continue to generate IDs for about 174 years from start_time by default.
But after the Sonyflake time is over the limit, next_id raises an error.
