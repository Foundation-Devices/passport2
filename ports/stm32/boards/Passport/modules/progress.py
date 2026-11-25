# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# progress.py - Keep the screen moving through long work that never awaits.
#
# The display is drawn by lvgl_task on the event loop, so a task that computes for
# seconds without awaiting freezes its spinner. spinner_task() calls begin() for its
# task, and code in long loops calls step() or refresh(): at most every _PERIOD_MS
# they draw the screen directly. They don't await, so no other task runs in the
# middle of the work.
#
# With a progress page, the task splits 0-100% into phases and each loop reports
# its own count: phase(start, end) before a pass, count(n) and step() inside it.

_PERIOD_MS = const(100)

_active = False
_page = None
_start = 0
_span = 0
_total = 0
_done = 0
_shown = -1
_last = 0


def begin(page=None):
    global _active, _page, _shown, _last
    from utime import ticks_ms
    _active = True
    _page = page
    _shown = -1
    _last = ticks_ms()
    phase(0, 0)


def end():
    global _active, _page
    _active = False
    _page = None


def phase(start, end):
    # The next pass runs from start% to end%.
    global _start, _span, _total, _done
    _start = start
    _span = end - start
    _total = 0
    _done = 0


def count(total):
    # The pass has this many steps.
    global _total, _done
    _total = total
    _done = 0


def step():
    global _done
    _done += 1
    refresh()


def refresh():
    global _last, _shown
    if not _active:
        return
    from utime import ticks_ms, ticks_diff
    now = ticks_ms()
    if ticks_diff(now, _last) < _PERIOD_MS:
        return
    import heaplog
    heaplog.start('ui')
    if _page is not None:
        percent = _start
        if _total:
            percent += _span * min(_done, _total) // _total
        if percent != _shown:
            _shown = percent
            _page.set_progress(percent)
    from tasks.lvgl_task import draw
    draw()
    heaplog.stop('ui')
    _last = ticks_ms()
