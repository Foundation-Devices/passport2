# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# address_explorer_page.py

import lvgl as lv
import passport
import microns
import common
from pages import BrightnessAdjustablePage
from views import QRCode, Label
from styles.style import Stylize
from styles.colors import TEXT_GREY, FD_BLUE
from constants import CARD_BORDER_WIDTH

class AddressExplorerForward:
    def __init__(self, last_version=None):
        self.last_version = last_version


class AddressExplorerBackward:
    def __init__(self, last_version=None):
        self.last_version = last_version


class AddressExplorerPage(BrightnessAdjustablePage):
    def __init__(self,
                 last_version=0,
                 address=None,
                 deriv_path=None,
                 card_header=None,
                 statusbar=None,
                 left_micron=microns.Back,
                 right_micron=microns.Checkmark):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         left_micron=left_micron,
                         right_micron=right_micron)

        self.address = address
        self.timer = None

        self.set_size(lv.pct(100), lv.pct(100))

        with Stylize(self) as default:
            default.pad(top=4)
            default.pad_row(6)

        # QR Code of the address.
        self.qrcode = QRCode(last_version=last_version)
        self.qrcode.set_width(lv.pct(100))
        self.qrcode.set_height(114)

        with Stylize(self.qrcode) as default:
            default.pad(left=CARD_BORDER_WIDTH, right=CARD_BORDER_WIDTH)
            default.align(lv.ALIGN.CENTER)
            default.flex_fill()

        self.add_child(self.qrcode)

        # Address label.
        self.address_label = Label(text=address, color=TEXT_GREY, center=True)
        self.address_label.set_size(lv.pct(100), lv.SIZE.CONTENT)
        self.add_child(self.address_label)

        # Derivation path label.
        self.derivation_path_label = Label(text=deriv_path, color=FD_BLUE, center=True)
        self.derivation_path_label.set_size(lv.pct(100), lv.SIZE.CONTENT)
        with Stylize(self.derivation_path_label) as default:
            default.pad(left=4, right=4)
        self.add_child(self.derivation_path_label)

        self.prev_top_level = None

    def attach(self, group):
        super().attach(group)
        self.timer = lv.timer_create(lambda timer: self.update(), 300, None)
        self.qrcode.attach(group)

        self.prev_top_level = common.ui.set_is_top_level(False)
        common.keypad.set_intercept_key_cb(self.on_key)

    def detach(self):
        self.qrcode.detach()

        common.keypad.set_intercept_key_cb(None)
        common.ui.set_is_top_level(self.prev_top_level)
        
        super().detach()

    def update(self):
        if self.is_attached():
            self.qrcode.update(self.address)

    def on_key(self, key, pressed):
        super().on_key(key, pressed)
        is_sim = passport.IS_SIMULATOR

        if pressed:
            # TODO: Fix this so the keycodes are the same here
            if key == lv.KEY.RIGHT or (is_sim and key == 114):
                self.set_result(AddressExplorerForward(last_version=self.qrcode.last_version()))
            elif key == lv.KEY.LEFT or (is_sim and key == 108):
                self.set_result(AddressExplorerBackward(last_version=self.qrcode.last_version()))

