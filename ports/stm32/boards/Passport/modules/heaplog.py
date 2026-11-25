# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# heaplog.py - Diagnostic build only: heap and timing log for PSBT validation and signing.
#
# Each mark() records the elapsed time, heap in use, heap free and the largest block that
# can still be allocated, and appends it to heaplog.csv on the microSD card. Lines are
# written as they happen, so a hang still leaves everything up to the last mark. Inside
# a CardSlot context (the microSD save) pass flush=False: CardSlot's exit unmounts the
# card, so writing from there would pull it out from under the save.

import gc

try:
    import utime
except ImportError:
    # The host tests run the PSBT code under CPython. mark() can't measure the heap
    # there and gives up quietly; start() and stop() still need a clock.
    import time

    class utime:
        ticks_ms = staticmethod(lambda: int(time.monotonic() * 1000))
        ticks_us = staticmethod(lambda: int(time.monotonic() * 1000000))
        ticks_diff = staticmethod(lambda end, begin: end - begin)

_FILE = 'heaplog.csv'

_t0 = utime.ticks_ms()
_pending = []
_spent_us = 0          # time spent inside mark() itself, so it can be subtracted
_totals = {}           # category -> [microseconds, count]
_started = {}


def start(category):
    _started[category] = utime.ticks_us()


def stop(category):
    began = _started.pop(category, None)
    if began is None:
        return
    elapsed = utime.ticks_diff(utime.ticks_us(), began)
    total = _totals.get(category)
    if total is None:
        _totals[category] = [elapsed, 1]
    else:
        total[0] += elapsed
        total[1] += 1


def reset():
    _totals.clear()
    _started.clear()


def _largest_block(limit):
    # Binary search for the biggest single allocation that still succeeds. With the
    # heap fragmented this is smaller than the total free.
    lo, hi = 0, limit
    while hi - lo > 32:
        mid = (lo + hi) // 2
        try:
            block = bytearray(mid)
            del block
            lo = mid
        except MemoryError:
            hi = mid
    return lo


def mark(label, extra='', flush=True):
    global _spent_us
    began = utime.ticks_us()
    try:
        gc.collect()
        used = gc.mem_alloc()
        free = gc.mem_free()
        largest = _largest_block(free)
        timings = ';'.join('%s=%dms/%d' % (k, v[0] // 1000, v[1]) for k, v in _totals.items())
        _pending.append('%d,%s,%d,%d,%d,%d,%s,%s\n' % (
            utime.ticks_diff(utime.ticks_ms(), _t0), label, used, free, largest,
            _spent_us // 1000, timings, extra))
        if flush:
            _write()
    except BaseException:
        # Out of memory or no card: keep going, the measurement must not change the outcome.
        pass
    _spent_us += utime.ticks_diff(utime.ticks_us(), began)


def error(label, e):
    # mark() with the exception and where it was raised, on one line.
    try:
        import uio
        import sys
        buf = uio.StringIO()
        sys.print_exception(e, buf)
        text = buf.getvalue().strip().replace(chr(10), ' | ').replace(',', ';')
    except BaseException:
        text = str(e)
    mark(label, text)


def flush():
    try:
        _write()
    except BaseException:
        pass


def _write():
    if not _pending:
        return
    from files import CardSlot
    with CardSlot():
        with open(CardSlot.get_sd_root() + '/' + _FILE, 'a') as f:
            for line in _pending:
                f.write(line)
    _pending.clear()
