# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import lvgl as lv
import tasks
import uasyncio as asyncio
import ui


async def init_lvgl():
    import common
    from display import Display
    common.display = Display()
    common.display.set_brightness(100)

    await tasks.lvgl_task()


async def test_ui():
    # TODO: test UI
    return_value.write(b'OK')
    asyncio.get_event_loop().stop()

loop = asyncio.get_event_loop()
loop.create_task(init_lvgl())
loop.create_task(test_ui())
loop.run_forever()
