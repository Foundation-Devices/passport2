# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# display.py - Screen rendering and brightness control
#

import passport
from passport import Backlight
import passport_lv
import lvgl as lv


class Display:

    if passport.IS_COLOR:
        WIDTH = 240
        FB_WIDTH = 240
        LINE_SIZE_BYTES = FB_WIDTH * 2
        HALF_WIDTH = WIDTH // 2
        HEIGHT = 320
        HALF_HEIGHT = HEIGHT // 2
        HEADER_HEIGHT = 40
        FOOTER_HEIGHT = 32
        SCROLLBAR_WIDTH = 8
        if passport.IS_SIMULATOR:
            # Use full-screen for simulator so we can more easily get screen captures
            NUM_LVGL_BUF_LINES = HEIGHT
        else:
            # NUM_LVGL_BUF_LINES = HEIGHT
            NUM_LVGL_BUF_LINES = 80
        LVGL_BUF_SIZE = (LINE_SIZE_BYTES * NUM_LVGL_BUF_LINES)
        NUM_PIXELS_IN_BUF = FB_WIDTH * NUM_LVGL_BUF_LINES
    else:
        WIDTH = 230
        # Note for the Sharp display the frame buffer width has to be 240 to draw properly
        FB_WIDTH = 240
        LINE_SIZE_BYTES = FB_WIDTH // 8
        HALF_WIDTH = WIDTH // 2
        HEIGHT = 303
        HALF_HEIGHT = HEIGHT // 2
        HEADER_HEIGHT = 38
        FOOTER_HEIGHT = 32
        SCROLLBAR_WIDTH = 8
        NUM_LVGL_BUF_LINES = HEIGHT
        LVGL_BUF_SIZE = (LINE_SIZE_BYTES * NUM_LVGL_BUF_LINES)
        NUM_PIXELS_IN_BUF = WIDTH * NUM_LVGL_BUF_LINES

    def __init__(self):
        if not lv.is_initialized():
            lv.init()

        # Initialize passport LCD.
        passport_lv.lcd.init()

        # LVGL --------------------------------------------------------------------------------------------------------

        self.backlight = Backlight()
        self.curr_brightness = 100

    def set_brightness(self, val):
        # 0-100 are valid
        if val >= 0 and val <= 100:
            self.backlight.intensity(val)
            self.curr_brightness = val
